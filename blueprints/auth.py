
from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin
import os

auth_bp = Blueprint("auth", __name__)

BASIC_AUTH_USERNAME = os.getenv("BASIC_AUTH_USERNAME", "admin")
BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD", "changeme")

login_manager = LoginManager()
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id):
        self.id = id
        self.name = id
        self.password = BASIC_AUTH_PASSWORD
    def get_id(self):
        return self.id

@login_manager.user_loader
def load_user(user_id):
    if user_id == BASIC_AUTH_USERNAME:
        return User(user_id)
    return None

@auth_bp.route("/login", methods=["GET", "POST"])
def login_route():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == BASIC_AUTH_USERNAME and password == BASIC_AUTH_PASSWORD:
            user = User(username)
            login_user(user)
            return redirect(url_for("auth.index"))
        else:
            error = "Invalid credentials."
    return render_template("login.html", error=error)

@auth_bp.route("/logout")
@login_required
def logout_route():
    logout_user()
    return redirect(url_for("auth.login_route"))

@auth_bp.route("/")
@login_required
def index():
    return render_template("index.html")
