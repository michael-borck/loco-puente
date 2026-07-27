#!/usr/bin/env bash
# librechat-users — account admin for chat.locopuente.org.
#
# LibreChat has NO admin UI for users. There is no user list, no role editor and
# no "resend verification" button anywhere in the web interface, for admins or
# anyone else. Account management is a set of npm scripts inside the container
# that write straight to Mongo. This wraps them, and fills the gaps they leave.
#
# WHY THIS LIVES IN deploy/ AND NOT IN puente.
# puente is a portable AI orchestrator; this shells into one named container and
# depends on that image's npm scripts. As `puente user ...` it would be dead
# weight in every deployment that doesn't run LibreChat, and puente's command
# surface would change shape depending on which optional services are enabled.
# Same reasoning as chat-window.sh, which sits here for the same reason.
#
# WHAT THE UPSTREAM SCRIPTS GET WRONG, AND WHAT WE DO INSTEAD.
#   * `npm run list-users` prints SIX LINES PER USER and omits both emailVerified
#     and role — the two fields that actually matter when a student can't log in.
#     Unusable at 74 students. `list` here queries Mongo directly for a table.
#   * Nothing upstream can force-verify an account. When mail delivery fails the
#     student is simply stuck. `verify` sets the flag directly.
#   * Argument conventions are INCONSISTENT between scripts: create-user needs a
#     `--` separator before its args (npm passes them to the script), while
#     invite-user and ban-user take them bare. Getting this wrong silently feeds
#     npm's own flags to the script. Each call below is written to match.
#
# Usage: librechat-users.sh <command> [args]        (no args = interactive menu)
set -euo pipefail

APP=puente-librechat
DB=puente-librechat-mongo
DBNAME=LibreChat

die() { printf 'error: %s\n' "$*" >&2; exit 1; }

# Every subcommand needs both containers. Checked once, up front, rather than
# letting `docker exec` fail halfway through a bulk import with a cryptic error.
require_containers() {
  docker inspect -f '{{.State.Running}}' "$APP" 2>/dev/null | grep -q true \
    || die "$APP is not running. Start it with: puente up librechat"
  docker inspect -f '{{.State.Running}}' "$DB" 2>/dev/null | grep -q true \
    || die "$DB is not running."
}

# mongosh --quiet with --eval. Kept in one place so the quoting is only wrong or
# right once. Callers pass a JS snippet; `db` is already the LibreChat database.
mongo_eval() {
  docker exec "$DB" mongosh "$DBNAME" --quiet --eval "$1"
}

# npm scripts that prompt (create-user asks for a password, reset-password asks
# for everything) need a TTY. When stdin is not a terminal — cron, a pipe, the
# csv-import loop — `docker exec -it` fails with "the input device is not a TTY",
# so allocate one only when we actually have one.
docker_run() {
  if [ -t 0 ]; then docker exec -it "$APP" "$@"; else docker exec -i "$APP" "$@"; fi
}

# ---------------------------------------------------------------------------
# Listing and lookup
# ---------------------------------------------------------------------------

# One line per user, newest last, with the fields that explain login failures.
# `role` is included because it is invisible everywhere else — a tutor who needs
# ADMIN looks identical to a student until you check here.
cmd_list() {
  local filter='{}'
  case "${1:-}" in
    unverified) filter='{emailVerified:false}' ;;
    admins)     filter='{role:"ADMIN"}' ;;
    '')         filter='{}' ;;
    *)          filter="{email:/$(printf '%s' "$1" | sed 's/[\/&]/\\&/g')/i}" ;;
  esac
  mongo_eval "
    const users = db.users.find($filter, {email:1,name:1,emailVerified:1,role:1,createdAt:1})
                    .sort({createdAt:1}).toArray();
    if (!users.length) { print('(no matching users)'); quit(); }
    const pad = (s,n) => String(s ?? '').padEnd(n).slice(0,n);
    print(pad('EMAIL',42)+pad('NAME',22)+pad('VER',5)+pad('ROLE',7)+'CREATED');
    print('-'.repeat(94));
    users.forEach(u => print(
      pad(u.email,42) + pad(u.name,22) +
      pad(u.emailVerified ? 'yes' : 'NO',5) +
      pad(u.role,7) + (u.createdAt ? u.createdAt.toISOString().slice(0,16) : '')
    ));
    print('');
    print('total: ' + users.length +
          '   unverified: ' + users.filter(u => !u.emailVerified).length);
  "
}

# Everything known about one account, for "why can't this student log in".
cmd_find() {
  local email="${1:?usage: find <email-or-fragment>}"
  local esc; esc=$(printf '%s' "$email" | sed 's/[\/&]/\\&/g')
  mongo_eval "
    const rx = /$esc/i;
    const users = db.users.find({\$or:[{email:rx},{name:rx},{username:rx}]}).toArray();
    if (!users.length) { print('NOT FOUND: $email'); quit(1); }
    users.forEach(u => {
      print('email:     ' + u.email);
      print('name:      ' + (u.name || '(none)'));
      print('username:  ' + (u.username || '(none)'));
      print('verified:  ' + u.emailVerified);
      print('role:      ' + u.role);
      print('provider:  ' + (u.provider || 'email'));
      print('created:   ' + (u.createdAt ? u.createdAt.toISOString() : '?'));
      print('id:        ' + u._id);
      print('sessions:  ' + db.sessions.countDocuments({user: u._id}));
      print('convos:    ' + db.conversations.countDocuments({user: u._id.toString()}));
      print('---');
    });
  "
}

# Near-duplicate detector, for reconciling against enrolment.
#
# Real case, 2026-07-27: 24378832@student registered 30s after 23378832@student
# — one transposed digit, almost certainly the same person typing it wrong the
# first time, leaving an unverified orphan. Comparing the LOCAL PART only (the
# student number) catches these; comparing whole addresses does not, because the
# domain dominates the distance. Threshold is 1 edit — 2 produces noise across a
# cohort of sequential student numbers.
cmd_dupes() {
  mongo_eval '
    const lev = (a,b) => {
      const m=a.length, n=b.length;
      if (Math.abs(m-n) > 1) return 99;
      const d=Array.from({length:m+1},(_,i)=>[i,...Array(n).fill(0)]);
      for (let j=0;j<=n;j++) d[0][j]=j;
      for (let i=1;i<=m;i++) for (let j=1;j<=n;j++)
        d[i][j]=Math.min(d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1]+(a[i-1]===b[j-1]?0:1));
      return d[m][n];
    };
    const us = db.users.find({}, {email:1,emailVerified:1,createdAt:1}).toArray()
                 .map(u => ({...u, local: u.email.split("@")[0]}));
    let found = 0;
    for (let i=0;i<us.length;i++) for (let j=i+1;j<us.length;j++) {
      if (lev(us[i].local, us[j].local) !== 1) continue;
      found++;
      print("possible duplicate pair:");
      [us[i],us[j]].forEach(u => print("   " + u.email +
        "   verified=" + u.emailVerified +
        "   " + (u.createdAt ? u.createdAt.toISOString().slice(0,16) : "")));
      print("");
    }
    if (!found) print("no near-duplicate addresses found.");
    else print("NOTE: an unverified twin of a verified account is usually a typo.");
  '
}

# ---------------------------------------------------------------------------
# Creating accounts
# ---------------------------------------------------------------------------

# create-user bypasses BOTH gates: the domain allowlist and email verification.
# That is the point — it is how you add someone once self-registration is closed,
# and how you rescue a student whose mail never arrives.
# Note the `--`: npm needs it to pass args through. invite/ban below do NOT.
cmd_create() {
  local email="${1:?usage: create <email> <name> <username>}"
  local name="${2:?usage: create <email> <name> <username>}"
  local username="${3:?usage: create <email> <name> <username>}"
  # It prompts for a password and will hang forever on a pipe. Fail fast.
  [ -t 0 ] || die "create prompts for a password; run it from a terminal (or use invite)"
  docker_run npm run create-user -- "$email" "$name" "$username"
}

# The preferred route after closing registration: the user picks their own
# password and no secret has to travel over email or a lecture theatre.
# Requires working SMTP — see the RESEND_API_KEY notes in puente.yml.
cmd_invite() {
  local email="${1:?usage: invite <email>}"
  docker_run npm run invite-user "$email"
}

# Bulk create from a CSV of email,name,username (header optional, # = comment).
#
# WHY INVITES ARE THE DEFAULT HERE: create-user PROMPTS for a password, so a
# non-interactive loop cannot drive it without passing the password as a 4th
# argument, which upstream explicitly discourages and which would put one shared
# password on every account in the file. `import` therefore sends invites unless
# you pass --with-password, which prompts once per row and needs a terminal.
cmd_import() {
  local file="${1:?usage: import <file.csv> [--with-password]}"
  local mode="${2:-invite}"
  [ -r "$file" ] || die "cannot read $file"
  [ "$mode" = "--with-password" ] && [ ! -t 0 ] \
    && die "--with-password prompts per row; run it from a terminal"

  local n=0 skipped=0
  while IFS=, read -r email name username _rest; do
    email=$(printf '%s' "${email:-}" | tr -d '\r' | xargs || true)
    [ -z "$email" ] && continue
    case "$email" in \#*) continue ;; email|Email|EMAIL) continue ;; esac
    name=$(printf '%s' "${name:-}" | tr -d '\r' | xargs || true)
    username=$(printf '%s' "${username:-}" | tr -d '\r' | xargs || true)

    if mongo_eval "quit(db.users.countDocuments({email:'$email'}) ? 0 : 1)" >/dev/null 2>&1; then
      printf 'skip (exists): %s\n' "$email"; skipped=$((skipped+1)); continue
    fi

    if [ "$mode" = "--with-password" ]; then
      [ -n "$name" ] && [ -n "$username" ] || die "row for $email needs name and username"
      printf '\n--- creating %s (you will be prompted for a password) ---\n' "$email"
      cmd_create "$email" "$name" "$username"
    else
      printf 'inviting: %s\n' "$email"
      cmd_invite "$email"
    fi
    n=$((n+1))
  done < "$file"
  printf '\nprocessed %d, skipped %d existing.\n' "$n" "$skipped"
}

# ---------------------------------------------------------------------------
# Unblocking students
# ---------------------------------------------------------------------------

# Force emailVerified=true. The escape hatch when SMTP itself is the problem —
# no upstream script does this, and without it the student cannot log in at all.
cmd_verify() {
  local email="${1:?usage: verify <email>}"
  mongo_eval "
    const r = db.users.updateOne({email:'$email'}, {\$set:{emailVerified:true}});
    if (!r.matchedCount) { print('NOT FOUND: $email'); quit(1); }
    print(r.modifiedCount ? 'verified: $email' : 'already verified: $email');
  "
}

# Re-send the verification email through the app's own endpoint, so the token is
# minted and mailed exactly as it is at signup.
#
# TWO THINGS TO TELL THE STUDENT:
#   * It is a LINK, not a code. The mail contains /verify?token=...&email=...
#     so "enter the code" is the wrong instruction.
#   * Each resend INVALIDATES the previous link (deleteEmailVerificationTokens).
#     If they clicked resend twice, only the newest mail works.
# The endpoint always returns 200, even for an address that does not exist —
# anti-enumeration upstream — so we check Mongo first to give an honest answer.
cmd_resend() {
  local email="${1:?usage: resend <email>}"
  mongo_eval "quit(db.users.countDocuments({email:'$email'}) ? 0 : 1)" >/dev/null 2>&1 \
    || die "no such user: $email (the API would report success anyway)"
  # The image ships no curl, and 3080 is not published to the host, so drive the
  # request with the container's own node (fetch is global on node >= 18).
  docker exec "$APP" node -e "
    fetch('http://localhost:3080/api/user/verify/resend', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({email: process.argv[1]}),
    })
      .then(r => r.text().then(t => { console.log('HTTP ' + r.status + '  ' + t);
                                      process.exit(r.ok ? 0 : 1); }))
      .catch(e => { console.error(e.message); process.exit(1); });
  " "$email"
  printf 'sent to %s — it is a LINK, and it invalidates any earlier one.\n' "$email"
}

# Resend to everyone still unverified. The end-of-lab sweep.
cmd_resend_all() {
  local emails
  emails=$(mongo_eval 'db.users.find({emailVerified:false},{email:1}).forEach(u=>print(u.email))')
  [ -n "$emails" ] || { echo "no unverified accounts."; return 0; }
  printf '%s\n' "$emails" | while read -r e; do
    [ -z "$e" ] && continue
    printf '%-45s ' "$e"
    cmd_resend "$e" >/dev/null 2>&1 && echo sent || echo FAILED
  done
}

cmd_password() {
  # reset-password prompts for email and password itself; no args to pass.
  [ -t 0 ] || die "password reset is interactive; run it from a terminal"
  docker_run npm run reset-password
}

# ---------------------------------------------------------------------------
# Roles, removal, registration gate
# ---------------------------------------------------------------------------

# Tutors need ADMIN. Nothing in the web UI can grant it.
cmd_role() {
  local email="${1:?usage: role <email> <ADMIN|USER>}"
  local role="${2:?usage: role <email> <ADMIN|USER>}"
  case "$role" in ADMIN|USER) ;; *) die "role must be ADMIN or USER" ;; esac
  mongo_eval "
    const r = db.users.updateOne({email:'$email'}, {\$set:{role:'$role'}});
    if (!r.matchedCount) { print('NOT FOUND: $email'); quit(1); }
    print('$email is now $role  (they must log out and back in)');
  "
}

# ban-user takes a duration in MINUTES, bare (no `--`).
cmd_ban() {
  local email="${1:?usage: ban <email> <minutes>}"
  local mins="${2:?usage: ban <email> <minutes>}"
  docker_run npm run ban-user "$email" "$mins"
}

# Deletes the account AND its data. Irreversible.
#
# NO CONFIRMATION PROMPT HERE ON PURPOSE. delete-user asks TWO questions of its
# own ("Really delete <email> (<id>) and ALL their data?", then whether to drop
# transaction history) and its wording is better than ours because it echoes the
# resolved user and id. A wrapper prompt on top would eat the first answer and
# leave the inner script waiting on a stdin that never comes — which is exactly
# what happened when this was written. Needs a terminal.
cmd_delete() {
  local email="${1:?usage: delete <email>}"
  [ -t 0 ] || die "delete is interactive (it asks twice); run it from a terminal"
  docker_run npm run delete-user "$email"
}

# Open/close self-registration.
#
# ALLOW_REGISTRATION is baked into the container environment at creation, so
# changing it is a RECREATE, not a restart — the same trap documented for
# ANTHROPIC_API_KEY in chat-window.sh. This only reports the current value and
# tells you what to edit; flipping it means editing puente.yml (the source of
# truth — the generated files under ~/.puente are overwritten on `puente up`).
cmd_registration() {
  local cur
  cur=$(docker exec "$APP" printenv ALLOW_REGISTRATION 2>/dev/null || echo '(unset)')
  printf 'ALLOW_REGISTRATION = %s\n\n' "$cur"
  cat <<'EOF'
To change it, edit puente.yml (NOT ~/.puente — that copy is regenerated),
then recreate the container:

    librechat:
      allow_registration: false

    puente up librechat        # recreate; a restart will NOT pick this up

Closing registration does not affect `create` or `invite` here: both bypass
the domain allowlist and the signup page entirely.
EOF
}

cmd_domains() {
  # Print the registration block only: from `registration:` up to the next
  # top-level key, exclusive. A plain sed range would include that next line.
  docker exec "$APP" awk '
    /^registration:/ {inblock=1}
    inblock && /^[a-z]/ && !/^registration:/ {exit}
    inblock {print}
  ' /app/librechat.yaml || true
  cat <<'EOF'

A rejected domain shows the student "You have tried to sign up too many times"
— the SAME message as the rate limiter. It is not rate limiting. Confirm with:

    docker logs puente-librechat --since 1h | grep 'Registration not allowed'

Edit allowed_registration_domains in puente.yml, then `puente up librechat`.
EOF
}

cmd_stats() {
  mongo_eval '
    print("users:        " + db.users.countDocuments());
    print("unverified:   " + db.users.countDocuments({emailVerified:false}));
    print("admins:       " + db.users.countDocuments({role:"ADMIN"}));
    print("conversations:" + db.conversations.countDocuments());
    print("");
    print("by domain:");
    db.users.aggregate([
      {$project:{d:{$arrayElemAt:[{$split:["$email","@"]},1]}}},
      {$group:{_id:"$d",n:{$sum:1}}},{$sort:{n:-1}}
    ]).forEach(x => print("   " + String(x.n).padStart(4) + "  " + x._id));
    print("");
    print("registrations by day (last 10):");
    db.users.aggregate([
      {$group:{_id:{$dateToString:{format:"%Y-%m-%d",date:"$createdAt"}},n:{$sum:1}}},
      {$sort:{_id:-1}},{$limit:10}
    ]).forEach(x => print("   " + x._id + "  " + x.n));
  '
}

# ---------------------------------------------------------------------------
# Interactive menu — for fixing one account mid-class without recalling syntax
# ---------------------------------------------------------------------------

menu() {
  while true; do
    cat <<'EOF'

  LibreChat user admin
  ────────────────────────────────────────────
   1) list users            2) list unverified
   3) find a user           4) find duplicates
   5) resend verification   6) resend to ALL unverified
   7) force-verify          8) reset a password
   9) create account       10) invite by email
  11) import from CSV      12) set role
  13) delete account       14) ban account
  15) stats                16) registration / domains
   q) quit
EOF
    printf '  > '
    local choice a b u
    read -r choice || return 0
    case "$choice" in
      1) cmd_list ;;
      2) cmd_list unverified ;;
      3) printf 'email or fragment: '; read -r a; cmd_find "$a" || true ;;
      4) cmd_dupes ;;
      5) printf 'email: '; read -r a; cmd_resend "$a" || true ;;
      6) cmd_resend_all ;;
      7) printf 'email: '; read -r a; cmd_verify "$a" || true ;;
      8) cmd_password || true ;;
      9) printf 'email: '; read -r a
         printf 'full name: '; read -r b
         printf 'username: '; read -r u; cmd_create "$a" "$b" "$u" || true ;;
     10) printf 'email: '; read -r a; cmd_invite "$a" || true ;;
     11) printf 'csv path: '; read -r a; cmd_import "$a" || true ;;
     12) printf 'email: '; read -r a
         printf 'role [ADMIN/USER]: '; read -r b; cmd_role "$a" "$b" || true ;;
     13) printf 'email: '; read -r a; cmd_delete "$a" || true ;;
     14) printf 'email: '; read -r a
         printf 'minutes: '; read -r b; cmd_ban "$a" "$b" || true ;;
     15) cmd_stats ;;
     16) cmd_registration; cmd_domains ;;
      q|Q) return 0 ;;
      *) echo "  ?" ;;
    esac
  done
}

usage() {
  cat <<'EOF'
librechat-users.sh — account admin for chat.locopuente.org

  (no arguments)              interactive menu

  list [unverified|admins|<fragment>]
  find <email-or-fragment>    everything known about one account
  dupes                       near-identical addresses (typo detector)
  stats                       counts by domain, day, verification

  resend <email>              re-send the verification LINK
  resend-all                  ...to every unverified account
  verify <email>              force emailVerified=true (SMTP escape hatch)
  password                    reset a password (prompts)

  create <email> <name> <username>    bypasses domain gate + verification
  invite <email>                      emailed invite; they set the password
  import <file.csv> [--with-password] bulk; invites unless told otherwise

  role <email> <ADMIN|USER>
  ban <email> <minutes>
  delete <email>              also deletes their chat history

  registration                show the signup gate and how to close it
  domains                     show the allowed email domains
EOF
}

main() {
  require_containers
  local cmd="${1:-menu}"; shift || true
  case "$cmd" in
    menu)          menu ;;
    list)          cmd_list "${1:-}" ;;
    find)          cmd_find "$@" ;;
    dupes)         cmd_dupes ;;
    stats)         cmd_stats ;;
    resend)        cmd_resend "$@" ;;
    resend-all)    cmd_resend_all ;;
    verify)        cmd_verify "$@" ;;
    password)      cmd_password ;;
    create)        cmd_create "$@" ;;
    invite)        cmd_invite "$@" ;;
    import)        cmd_import "$@" ;;
    role)          cmd_role "$@" ;;
    ban)           cmd_ban "$@" ;;
    delete)        cmd_delete "$@" ;;
    registration)  cmd_registration ;;
    domains)       cmd_domains ;;
    -h|--help|help) usage ;;
    *)             usage; exit 1 ;;
  esac
}

main "$@"
