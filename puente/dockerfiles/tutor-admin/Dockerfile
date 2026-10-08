# tutor-admin — the web half of the tutor admin UI.
#
# This exists only to pin pymongo. The app itself is a single stdlib file that
# `pre_start` copies into the bind mount on every `puente up`, so the image
# carries no application code — only the interpreter and the one third-party
# dependency it imports. Code changes therefore still ship without a rebuild.
#
# Previously the container ran `pip install pymongo` as its entrypoint, on every
# start. That was worth fixing for three reasons: the container needed outbound
# PyPI access to start at all (so a firewalled or air-gapped host could not run
# it), the version was whatever upstream published that day, and a slow or failed
# install looked indistinguishable from an app that had hung.
FROM python:3.12-slim

# Pinned: pymongo is the app's only dependency and an unpinned upgrade is a
# silent behaviour change in an account-administration surface.
# Bump deliberately, with a `puente up tutor_admin` to verify.
RUN pip install --no-cache-dir "pymongo==4.17.0"

WORKDIR /data
# Fail at build time rather than at first request if the app can't even import.
CMD ["python", "-c", "import pymongo; print('pymongo', pymongo.version)"]