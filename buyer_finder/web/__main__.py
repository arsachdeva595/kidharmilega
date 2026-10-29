"""
  python3 -m buyer_finder.web set-password     # create or change the login
  python3 -m buyer_finder.web run              # dev server on http://localhost:8000
"""

import getpass, json, sys

from werkzeug.security import generate_password_hash

from .. import ensure_dirs


def set_password():
    from .app import AUTH_FILE
    ensure_dirs()
    user = input("Username: ").strip()
    pw = getpass.getpass("Password (12+ characters): ")
    if len(pw) < 12:
        sys.exit("Use at least 12 characters.")
    if getpass.getpass("Again: ") != pw:
        sys.exit("Passwords don't match.")
    AUTH_FILE.write_text(json.dumps({"username": user, "hash": generate_password_hash(pw)}))
    AUTH_FILE.chmod(0o600)
    print(f"Saved login for '{user}' → {AUTH_FILE}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "set-password":
        set_password()
    elif cmd == "run":
        from .app import app
        app.run(host="127.0.0.1", port=8000, debug=False)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
