from flask import redirect, render_template, request, session, flash
from functools import wraps
from models import db, Usuario

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session['user_type'] = session.get("rol")
        if session["user_type"] != 'admin':
            flash("Acceso prohibido, por favor contacta al administrador del sistema para visitar ese enlace.", 'warning')
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

def is_password_confirmed(password, confirmation):
    if password != confirmation:
        flash("Error al confirmar contraseña")
        return redirect("/registro")
    return True

def user_already_exists(username):
    user = db.session.query(Usuario).filter_by(usuario=username).first()
    if not user:
        return False
    return True

def create_graph(type, query, df):
    pass