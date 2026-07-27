"""Tutor admin — a narrow web UI over LibreChat's user database.

WHY THIS EXISTS
LibreChat's own admin API is read-only (`/api/admin/users` exposes listUsers and
searchUsers, nothing else), so an ADMIN tutor can see who registered and do
nothing about it. Everything that actually unblocks a student — resend the
verification link, force-verify when SMTP fails, create an account after
self-registration closes — is a CLI script inside the container. Tutors do not
have shell on this box and should not need it.

WHAT IT DELIBERATELY CANNOT DO
No delete, no ban, no role changes. Those stay on the operator's CLI
(deploy/librechat-users.sh). The reasoning is blast radius, not distrust:
delete destroys chat history irreversibly, and granting ADMIN is privilege
escalation that would let a tutor grant it to anyone, including a student.
Every action here is either reversible or additive.

AUTHENTICATION IS NOT HANDLED HERE
Caddy terminates HTTP Basic before anything reaches this process (see the
`proxy:` block in puente.yml). This app therefore trusts that it is only
reachable through Caddy, which is enforced by binding to 127.0.0.1 in the
compose fragment — never publish this port. The tutor's identity arrives in
X-Tutor-User, set by Caddy from the authenticated username, and is written to
the audit log; it is used for attribution only and never for authorisation.

A NOTE ON WRITES, AND WHY THERE IS NO DOCKER SOCKET HERE
Reads and force-verify go straight to Mongo. Resend calls LibreChat's own HTTP
endpoint. But create and invite are npm scripts inside the LibreChat container:
they hash passwords and mint invite tokens using LibreChat's internals, and
reimplementing either would drift out of sync with the app it administers.

The obvious way to reach them is `docker exec`, which needs the Docker socket
mounted writable — and a writable socket is root on the host. Mounting it into
an internet-facing web service means one bug here escalates to the whole
machine, including the Anthropic key and every other service. That trade is not
worth a convenience feature, so this process has no socket and cannot exec
anything.

Instead it writes a JSON request into a spool directory and waits for a result
file. A small host-side runner (deploy/tutor-admin-runner.sh, a systemd timer)
owns the Docker socket, validates each request, and executes the npm script.
The privileged half runs outside the container, is a few dozen lines long, and
accepts only two verbs; the web app can ask for work but can never run it.
Worst case, a compromised web app queues account creations it could already
make legitimately through the UI.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from pymongo import MongoClient

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://librechat-mongo:27017/LibreChat")
LIBRECHAT_URL = os.environ.get("LIBRECHAT_URL", "http://librechat:3080")
AUDIT_LOG = os.environ.get("AUDIT_LOG", "/data/audit.log")
PORT = int(os.environ.get("PORT", "8091"))
# Handshake directory with the host-side runner; see _spool().
SPOOL_DIR = os.environ.get("SPOOL_DIR", "/data/spool")
SPOOL_TIMEOUT = int(os.environ.get("SPOOL_TIMEOUT", "60"))
# Ownership for spooled files, so the host-side runner (which runs as the
# operator, not root) can read what this container writes. -1 disables the
# chown. Defaults match the usual single-user host account.
SPOOL_UID = int(os.environ.get("SPOOL_UID", "1000"))
SPOOL_GID = int(os.environ.get("SPOOL_GID", "1000"))

# Addresses outside these domains cannot be created here. The signup page
# enforces its own allowlist from librechat.yaml, but create/invite bypass that
# gate by design, so without this a tutor could add any address at all. Falls
# back to the same list the signup page uses.
ALLOWED_DOMAINS = [
    d.strip().lower()
    for d in os.environ.get("ALLOWED_DOMAINS", "curtin.edu.au,student.curtin.edu.au,postgrad.curtin.edu.au").split(",")
    if d.strip()
]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
_db = _client.get_default_database()


def audit(actor: str, action: str, target: str, ok: bool, detail: str = "") -> None:
    """Append-only record of every mutating action.

    Written before the caller sees a response so a crash mid-action still
    leaves a trace. Failures to log are swallowed: losing an audit line must
    not take the tool down mid-class.
    """
    line = json.dumps(
        {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "actor": actor,
            "action": action,
            "target": target,
            "ok": ok,
            "detail": detail,
        }
    )
    try:
        with open(AUDIT_LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def domain_allowed(email: str) -> bool:
    return email.rsplit("@", 1)[-1].lower() in ALLOWED_DOMAINS


def list_users(scope: str = "", query: str = "") -> list[dict[str, Any]]:
    filt: dict[str, Any] = {}
    if scope == "unverified":
        filt = {"emailVerified": False}
    elif scope == "admins":
        filt = {"role": "ADMIN"}
    if query:
        rx = {"$regex": re.escape(query), "$options": "i"}
        filt = {**filt, "$or": [{"email": rx}, {"name": rx}, {"username": rx}]}
    cur = _db.users.find(
        filt, {"email": 1, "name": 1, "emailVerified": 1, "role": 1, "createdAt": 1}
    ).sort("createdAt", -1)
    out = []
    for u in cur:
        out.append(
            {
                "email": u.get("email", ""),
                "name": u.get("name") or "",
                "verified": bool(u.get("emailVerified")),
                "role": u.get("role", "USER"),
                "created": u["createdAt"].strftime("%Y-%m-%d %H:%M") if u.get("createdAt") else "",
            }
        )
    return out


def find_duplicates() -> list[list[dict[str, Any]]]:
    """Near-identical addresses, compared on the LOCAL PART only.

    Student numbers differ by one transposed digit far more often than by
    anything else, and comparing whole addresses buries that under a shared
    domain. Distance 1 exactly: 2 produces noise across sequential numbers.
    """

    def lev(a: str, b: str) -> int:
        if abs(len(a) - len(b)) > 1:
            return 99
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            cur = [i]
            for j, cb in enumerate(b, 1):
                cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
            prev = cur
        return prev[-1]

    users = [
        {
            "email": u["email"],
            "local": u["email"].split("@")[0],
            "verified": bool(u.get("emailVerified")),
            "created": u["createdAt"].strftime("%Y-%m-%d %H:%M") if u.get("createdAt") else "",
        }
        for u in _db.users.find({}, {"email": 1, "emailVerified": 1, "createdAt": 1})
    ]
    pairs = []
    for i in range(len(users)):
        for j in range(i + 1, len(users)):
            if lev(users[i]["local"], users[j]["local"]) == 1:
                pairs.append([users[i], users[j]])
    return pairs


def resend_verification(email: str) -> tuple[bool, str]:
    """Ask LibreChat to re-send its own verification mail.

    Two behaviours worth knowing, both upstream's:
      * The endpoint returns 200 even for unknown addresses (anti-enumeration),
        so we check Mongo first to give the tutor an honest answer.
      * Each resend invalidates the previous link, so a student who clicks
        resend twice must use the newest mail.
    """
    if not _db.users.count_documents({"email": email}, limit=1):
        return False, "no such user (the API would report success anyway)"
    req = urllib.request.Request(
        f"{LIBRECHAT_URL}/api/user/verify/resend",
        data=json.dumps({"email": email}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200, f"HTTP {r.status}"
    except urllib.error.URLError as e:
        return False, str(e)


def force_verify(email: str) -> tuple[bool, str]:
    r = _db.users.update_one({"email": email}, {"$set": {"emailVerified": True}})
    if not r.matched_count:
        return False, "no such user"
    return True, "verified" if r.modified_count else "already verified"


def _spool(verb: str, payload: dict[str, str]) -> tuple[bool, str]:
    """Queue a privileged action for the host-side runner and await its verdict.

    Written to a .tmp then renamed, so the runner never sees a half-written
    file. We then poll for <id>.result. The wait is bounded: a tutor gets a
    clear "queued but not confirmed" rather than a hung page if the runner is
    stopped, and the account usually appears moments later anyway.
    """
    req_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    body = json.dumps({"id": req_id, "verb": verb, **payload})
    try:
        os.makedirs(SPOOL_DIR, exist_ok=True)
        tmp = os.path.join(SPOOL_DIR, f"{req_id}.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(body)
        # 0640, and owned by the host user running the runner.
        #
        # This container runs as root, so a default-umask file lands as
        # root:root 0600 and the runner — which runs as the operator, NOT as
        # root, precisely because it holds the Docker socket — cannot read its
        # own queue. Group-readable plus a chown to SPOOL_UID/GID bridges that
        # without making a file containing a plaintext password world-readable.
        os.chmod(tmp, 0o640)
        if SPOOL_UID >= 0:
            try:
                os.chown(tmp, SPOOL_UID, SPOOL_GID)
            except OSError:
                pass  # not root, or already correct — the chmod may suffice
        os.rename(tmp, os.path.join(SPOOL_DIR, f"{req_id}.json"))
    except OSError as e:
        return False, f"could not queue request: {e}"

    result_path = os.path.join(SPOOL_DIR, f"{req_id}.result")
    for _ in range(SPOOL_TIMEOUT * 4):
        if os.path.exists(result_path):
            try:
                with open(result_path, encoding="utf-8") as fh:
                    res = json.load(fh)
                os.unlink(result_path)
            except (OSError, ValueError) as e:
                return False, f"unreadable result: {e}"
            return bool(res.get("ok")), str(res.get("detail", ""))[-2000:]
        time.sleep(0.25)
    return False, (
        "queued, but the runner did not respond within "
        f"{SPOOL_TIMEOUT}s — check that tutor-admin-runner is active"
    )


def create_user(email: str, name: str, username: str, password: str) -> tuple[bool, str]:
    return _spool(
        "create", {"email": email, "name": name, "username": username, "password": password}
    )


def invite_user(email: str) -> tuple[bool, str]:
    return _spool("invite", {"email": email})


PAGE = """<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Tutor admin — LibreChat</title>
<style>
:root{--bg:#fff;--fg:#111;--mut:#666;--line:#e3e3e3;--acc:#0b6bcb;--bad:#b3261e;--ok:#1b5e20;--card:#fafafa}
@media(prefers-color-scheme:dark){:root{--bg:#16181c;--fg:#e8e8e8;--mut:#9aa0a6;--line:#2c2f34;--acc:#7cb3f0;--bad:#f2b8b5;--ok:#7fd193;--card:#1e2126}}
*{box-sizing:border-box}
body{margin:0;font:15px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--fg)}
header{padding:14px 18px;border-bottom:1px solid var(--line);display:flex;gap:14px;align-items:baseline;flex-wrap:wrap}
h1{font-size:16px;margin:0;font-weight:600}
.who{color:var(--mut);font-size:13px;margin-left:auto}
main{padding:18px;max-width:1100px}
nav{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px}
nav a{padding:6px 12px;border:1px solid var(--line);border-radius:999px;text-decoration:none;color:var(--fg);font-size:14px}
nav a.on{background:var(--acc);border-color:var(--acc);color:#fff}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
th{color:var(--mut);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
td.email{white-space:normal;word-break:break-all}
.no{color:var(--bad);font-weight:600}
.yes{color:var(--ok)}
.wrap{overflow-x:auto}
form.inline{display:inline}
button{font:inherit;padding:4px 10px;border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:6px;cursor:pointer}
button:hover{border-color:var(--acc);color:var(--acc)}
button.primary{background:var(--acc);border-color:var(--acc);color:#fff}
.card{border:1px solid var(--line);border-radius:10px;padding:16px;margin-bottom:16px;background:var(--card)}
.card h2{margin:0 0 4px;font-size:15px}
.card p{margin:0 0 12px;color:var(--mut);font-size:13px}
label{display:block;margin-bottom:8px;font-size:13px}
label span{display:block;color:var(--mut);margin-bottom:3px}
input{font:inherit;padding:7px 9px;border:1px solid var(--line);border-radius:6px;width:100%;max-width:340px;background:var(--bg);color:var(--fg)}
.msg{padding:10px 12px;border-radius:8px;margin-bottom:14px;font-size:14px}
.msg.ok{background:#e6f4ea;color:#0f5132}.msg.err{background:#fce8e6;color:#842029}
@media(prefers-color-scheme:dark){.msg.ok{background:#12321c;color:#9be0ae}.msg.err{background:#3b1513;color:#f2b8b5}}
.hint{color:var(--mut);font-size:13px;border-left:3px solid var(--line);padding-left:10px;margin:12px 0}
.pair{border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin-bottom:10px;background:var(--card);font-size:14px}
</style>
"""
# The CSS above is full of literal percent signs (width:100%, every @media
# rule) and braces, so NEITHER %-formatting nor str.format can be used on it —
# both read those as markup and raise. The page is assembled by concatenation
# instead; see render_page().


def render_page(who: str, nav: str, msg: str, body: str) -> str:
    return (
        PAGE
        + f"<header><h1>Tutor admin — LibreChat</h1><span class=who>{who}</span></header>\n"
        + f"<main>\n<nav>{nav}</nav>\n{msg}\n{body}\n</main>\n"
    )


class Handler(BaseHTTPRequestHandler):
    server_version = "puente-tutor-admin"

    def log_message(self, *a):  # quieter container logs
        pass

    # Caddy authenticates and passes the username through. Absent (direct hit,
    # which should be impossible given the localhost bind) we still render, but
    # the audit trail records it honestly rather than inventing a name.
    def _who(self) -> str:
        return self.headers.get("X-Tutor-User") or "unknown"

    def _send(self, html: str, code: int = 200) -> None:
        b = html.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _page(self, tab: str, body: str, msg: str = "", err: str = "") -> None:
        tabs = [("", "Users"), ("unverified", "Unverified"), ("dupes", "Duplicates"), ("add", "Add account")]
        nav = "".join(
            f'<a class="{"on" if tab == t else ""}" href="/{t}">{label}</a>' for t, label in tabs
        )
        m = ""
        if msg:
            m = f'<div class="msg ok">{esc(msg)}</div>'
        elif err:
            m = f'<div class="msg err">{esc(err)}</div>'
        self._send(render_page(esc(self._who()), nav, m, body))

    def do_GET(self) -> None:
        path = self.path.split("?")[0].rstrip("/") or "/"
        query = ""
        if "?" in self.path:
            from urllib.parse import parse_qs

            query = parse_qs(self.path.split("?", 1)[1]).get("q", [""])[0]

        if path == "/health":
            self._send("ok")
            return
        if path == "/dupes":
            self._page("dupes", render_dupes(find_duplicates()))
            return
        if path == "/add":
            self._page("add", render_add())
            return
        if path == "/unverified":
            self._page("unverified", render_users(list_users("unverified"), query, unverified=True))
            return
        self._page("", render_users(list_users("", query), query))

    def do_POST(self) -> None:
        from urllib.parse import parse_qs

        n = int(self.headers.get("Content-Length") or 0)
        form = {k: v[0].strip() for k, v in parse_qs(self.rfile.read(n).decode()).items()}
        action = form.get("action", "")
        email = form.get("email", "")
        who = self._who()
        msg = err = ""

        if action == "resend":
            ok, detail = resend_verification(email)
            audit(who, "resend", email, ok, detail)
            msg = f"Verification link re-sent to {email}. It is a LINK, not a code — and it invalidates any earlier one." if ok else ""
            err = "" if ok else f"Could not resend to {email}: {detail}"

        elif action == "verify":
            ok, detail = force_verify(email)
            audit(who, "force-verify", email, ok, detail)
            msg = f"{email} is now marked verified ({detail})." if ok else ""
            err = "" if ok else f"Could not verify {email}: {detail}"

        elif action in ("create", "invite"):
            if not EMAIL_RE.match(email):
                err = f"{email or '(blank)'} is not a valid email address."
            elif not domain_allowed(email):
                err = (
                    f"{email} is outside the permitted domains "
                    f"({', '.join(ALLOWED_DOMAINS)}). Accounts made here bypass the "
                    "signup page's own check, so this limit is enforced separately."
                )
            elif _db.users.count_documents({"email": email}, limit=1):
                err = f"{email} already has an account."
            elif action == "invite":
                ok, detail = invite_user(email)
                audit(who, "invite", email, ok, detail)
                msg = f"Invitation emailed to {email}; they choose their own password." if ok else ""
                err = "" if ok else f"Invite failed for {email}: {detail}"
            else:
                name = form.get("name", "")
                username = form.get("username", "")
                password = form.get("password", "")
                if not (name and username and password):
                    err = "Name, username and password are all required."
                elif len(password) < 8:
                    err = "Password must be at least 8 characters."
                else:
                    ok, detail = create_user(email, name, username, password)
                    audit(who, "create", email, ok, detail)
                    msg = (
                        f"Account created for {email}, already verified — they can sign in now."
                        if ok
                        else ""
                    )
                    err = "" if ok else f"Could not create {email}: {detail}"
        else:
            err = "Unknown action."

        tab = "add" if action in ("create", "invite") else "unverified"
        body = render_add() if tab == "add" else render_users(list_users("unverified"), "", unverified=True)
        self._page(tab, body, msg, err)


def esc(s: Any) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_users(users: list[dict], query: str = "", unverified: bool = False) -> str:
    rows = []
    for u in users:
        actions = ""
        if not u["verified"]:
            actions = (
                f'<form class=inline method=post><input type=hidden name=action value=resend>'
                f'<input type=hidden name=email value="{esc(u["email"])}">'
                f'<button title="Send the verification link again">Resend</button></form> '
                f'<form class=inline method=post onsubmit="return confirm('
                f"'Mark {esc(u['email'])} verified without email confirmation?')\">"
                f'<input type=hidden name=action value=verify>'
                f'<input type=hidden name=email value="{esc(u["email"])}">'
                f'<button title="Bypass email confirmation entirely">Force-verify</button></form>'
            )
        rows.append(
            f'<tr><td class=email>{esc(u["email"])}</td><td>{esc(u["name"])}</td>'
            f'<td class="{"yes" if u["verified"] else "no"}">{"yes" if u["verified"] else "NO"}</td>'
            f'<td>{esc(u["role"])}</td><td>{esc(u["created"])}</td><td>{actions}</td></tr>'
        )
    if not rows:
        rows = ['<tr><td colspan=6 style="color:var(--mut)">No matching accounts.</td></tr>']
    search = (
        f'<form method=get style="margin-bottom:12px">'
        f'<input name=q value="{esc(query)}" placeholder="Search email, name or username" '
        f'style="max-width:320px"> <button>Search</button></form>'
    )
    note = ""
    if unverified:
        note = (
            '<div class=hint>These accounts registered but never confirmed, so they '
            "cannot sign in. <b>Resend</b> mails the link again (each resend cancels the "
            "previous one). <b>Force-verify</b> skips confirmation altogether — use it when "
            "the mail itself is not arriving.</div>"
        )
    return (
        note
        + search
        + '<div class=wrap><table><tr><th>Email<th>Name<th>Verified<th>Role<th>Registered<th></tr>'
        + "".join(rows)
        + f'</table></div><p style="color:var(--mut);font-size:13px">{len(users)} account(s).</p>'
    )


def render_dupes(pairs: list[list[dict]]) -> str:
    if not pairs:
        return (
            '<div class=hint>No near-identical addresses found.</div>'
            "<p>This looks for addresses differing by a single character, which is how a "
            "mistyped student number usually shows up.</p>"
        )
    out = [
        '<div class=hint>These addresses differ by one character, so one is probably a typo. '
        "An <b>unverified</b> account paired with a <b>verified</b> one is almost always the "
        "discarded first attempt — check before removing anything; removal is operator-only.</div>"
    ]
    for a, b in pairs:
        out.append(
            "<div class=pair>"
            + "".join(
                f'<div>{esc(u["email"])} — {"verified" if u["verified"] else "<b class=no>unverified</b>"}'
                f' · registered {esc(u["created"])}</div>'
                for u in (a, b)
            )
            + "</div>"
        )
    return "".join(out)


def render_add() -> str:
    return f"""
<div class=card>
  <h2>Invite by email</h2>
  <p>Sends an invitation; the student sets their own password. Preferred once
     self-registration is closed — no password has to be passed around.</p>
  <form method=post>
    <input type=hidden name=action value=invite>
    <label><span>Email</span><input name=email type=email required
      placeholder="student@student.curtin.edu.au"></label>
    <button class=primary type=submit>Send invitation</button>
  </form>
</div>
<div class=card>
  <h2>Create an account directly</h2>
  <p>Creates the account already verified, skipping both the signup page and the
     confirmation email. Use when email delivery is the problem, or the student
     is standing in front of you. You will need to tell them the password.</p>
  <form method=post>
    <input type=hidden name=action value=create>
    <label><span>Email</span><input name=email type=email required></label>
    <label><span>Full name</span><input name=name required></label>
    <label><span>Username</span><input name=username required></label>
    <label><span>Password (min 8 characters)</span><input name=password type=text required
      minlength=8></label>
    <button class=primary type=submit>Create account</button>
  </form>
</div>
<div class=hint>Permitted domains: {esc(', '.join(ALLOWED_DOMAINS))}.
Deleting accounts, banning, and changing roles are intentionally not available
here — ask the operator.</div>
"""


def main() -> None:
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    srv.serve_forever()


if __name__ == "__main__":
    main()
