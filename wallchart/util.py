import bcrypt
from flask import session, redirect, url_for
from functools import wraps

def login_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return inner


def bcryptify(password: str):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode("utf-8")
