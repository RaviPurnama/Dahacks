from functools import wraps
from flask import redirect, session

def login_required(f):
    ## login_required was taken From CS50's finance week 9

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

def dollars(money):
    return f"${money:,.2f}"