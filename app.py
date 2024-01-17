from flask import Flask, render_template, redirect, session, flash
from flask_debugtoolbar import DebugToolbarExtension
from models import connect_db, db, User, Feedback
from forms import UserForm, LoginForm, FeedbackForm
from secret_word import APP_SECRET_KEY
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql:///auth_ex"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
app.config["SECRET_KEY"] = APP_SECRET_KEY
app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False

connect_db(app)

toolbar = DebugToolbarExtension(app)


@app.route("/")
def homepage():
    return redirect("/register")


@app.route("/users/<username>")
def user_page(username):
    user = User.query.get_or_404(username)
    if "user_un" not in session:
        flash("Please login first!", "danger")
        return redirect("/")
    if session["user_un"] != user.username:
        flash("Can only see your own account!", "danger")
        return redirect("/login")

    fb = Feedback.query.filter_by(username=user.username)
    return render_template("user.html", user=user, feedback=fb)


@app.route("/register", methods=["GET", "POST"])
def register_user():
    form = UserForm()
    if "user_un" in session:
        username = session["user_un"]
        return redirect(f"/users/{username}")

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        email = form.email.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        new_user = User.register(username, password, email, first_name, last_name)

        db.session.add(new_user)

        try:
            db.session.commit()
        except IntegrityError:
            form.username.errors.append("Username taken. Please pick another.")
            form.email.errors.append("Email taken. Please pick another.")
            return render_template("register.html", form=form)
        session["user_un"] = new_user.username
        flash("Welcome! Successfully Created Your Account!", "success")
        return redirect(f"/users/{new_user.username}")

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login_user():
    form = LoginForm()
    if "user_un" in session:
        username = session["user_un"]
        return redirect(f"/users/{username}")

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.authenticate(username, password)

        if user:
            flash(f"Welcome Back, {user.first_name} {user.last_name}!", "success")
            session["user_un"] = user.username
            return redirect(f"/users/{user.username}")
        else:
            form.username.errors = ["Invalid username/password."]

    return render_template("login.html", form=form)


@app.route("/logout")
def logout_user():
    session.pop("user_un")
    flash("See you Later!", "info")
    return redirect("/")


@app.route("/users/<username>/delete", methods=["POST"])
def delete_user(username):
    user = User.query.get_or_404(username)
    if "user_un" not in session:
        flash("Please login first!", "danger")
        return redirect("/")
    if session["user_un"] != user.username:
        flash("Cannot delete someone else's account!", "danger")
        return redirect("/")

    Feedback.query.filter_by(username=username).delete()
    User.query.filter_by(username=username).delete()
    db.session.commit()
    session.pop("user_un")
    flash("Successfully deleted account!", "secondary")
    return redirect("/")


@app.route("/users/<username>/feedback/add", methods=["GET", "POST"])
def add_feedback(username):
    user = User.query.get_or_404(username)
    if "user_un" not in session:
        flash("Please login first!", "danger")
        return redirect("/")

    if session["user_un"] != user.username:
        flash("Cannot give feedback for someone else!", "danger")
        return redirect("/")

    form = FeedbackForm()
    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data
        new_fb = Feedback(title=title, content=content, username=user.username)
        db.session.add(new_fb)
        db.session.commit()
        flash("Your feedback has been added!", "success")
        return redirect(f"/users/{user.username}")
    return render_template("add_feedback.html", form=form, user=user)


@app.route("/feedback/<int:feedback_id>/update", methods=["GET", "POST"])
def update_feedback(feedback_id):
    feedback = Feedback.query.get_or_404(feedback_id)

    if "user_un" not in session:
        flash("Please login first!", "danger")
        return redirect("/")

    if session["user_un"] != feedback.username:
        flash("Cannot edit someone else's feedback!", "danger")
        return redirect("/")

    form = FeedbackForm(obj=feedback)
    if form.validate_on_submit():
        feedback.title = form.title.data
        feedback.content = form.content.data
        db.session.commit()
        flash("Your feedback has been changed!", "success")
        return redirect(f"/users/{feedback.username}")

    return render_template("edit_feedback.html", feedback=feedback, form=form)


@app.route("/feedback/<int:feedback_id>/delete", methods=["POST"])
def delete_feedback(feedback_id):
    feedback = Feedback.query.get_or_404(feedback_id)

    if "user_un" not in session:
        flash("Please login first!", "danger")
        return redirect("/")

    if session["user_un"] != feedback.username:
        flash("Cannot delete someone else's feedback!", "danger")
        return redirect("/")

    Feedback.query.filter_by(id=feedback_id).delete()
    db.session.commit()
    flash("Deleted Feedback!", "secondary")
    return redirect("/")


@app.errorhandler(404)
def not_found(e):
    flash("What you're looking for does not exist", "danger")
    return redirect("/")
