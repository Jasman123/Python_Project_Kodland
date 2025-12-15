from flask import Flask, render_template, request, redirect, url_for, session
import requests
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import random
from questions import quiz_questions

app = Flask(__name__)
app.secret_key = "super-secret-key-123"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

MAX_QUESTIONS = 10


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), unique=True, nullable=False)
    nama = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)

    # Quiz session
    quiz_score = db.Column(db.Integer, default=0)
    quiz_answered = db.Column(db.Integer, default=0)
    quiz_correct = db.Column(db.Integer, default=0)

    # Leaderboard cumulative
    total_score = db.Column(db.Integer, default=0)



def init_quiz():
    questions = quiz_questions.copy()
    random.shuffle(questions)
    session["remaining_questions"] = questions[:MAX_QUESTIONS]
    session["current_question"] = None

def get_next_question():
    if not session.get("remaining_questions"):
        return None
    question = session["remaining_questions"].pop(0)
    session["current_question"] = question
    return question



@app.route("/", methods=["GET", "POST"])
def home():
    session.clear()
    data_cuaca = None
    now = datetime.now()
    today = now.strftime("%A, %d %B %Y %H:%M:%S")

    if request.method == "POST":
        kota = request.form.get("kota")
        API_KEY = "0387275c79394f1892c142747251312"
        BASE_URL = "http://api.weatherapi.com/v1"

        response = requests.get(
            f"{BASE_URL}/forecast.json",
            params={"key": API_KEY, "q": kota, "days": 3}
        ).json()

        if "error" in response:
            data_cuaca = {"error": response["error"]["message"]}
        else:
            forecast = response["forecast"]["forecastday"]
            data_cuaca = {
                "kota": kota,
                "today": {
                    "temp": response["current"]["temp_c"],
                    "condition": response["current"]["condition"]["text"],
                    "min_temp": forecast[0]["day"]["mintemp_c"],
                    "max_temp": forecast[0]["day"]["maxtemp_c"]
                },
                "tomorrow": {
                    "temp": forecast[1]["day"]["avgtemp_c"],
                    "condition": forecast[1]["day"]["condition"]["text"]
                },
                "day_after_tomorrow": {
                    "temp": forecast[2]["day"]["avgtemp_c"],
                    "condition": forecast[2]["day"]["condition"]["text"]
                }
            }

    return render_template("home.html", cuaca=data_cuaca, today=today)



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        password = request.form.get("password")

        user = User.query.filter_by(user_id=user_id).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.user_id
            session["nama"] = user.nama

            # Reset quiz session only
            session.pop("remaining_questions", None)
            session.pop("current_question", None)
            user.quiz_score = 0
            user.quiz_answered = 0
            user.quiz_correct = 0
            db.session.commit()

            return redirect(url_for("quiz_page"))
        else:
            return render_template("login.html", error="User ID atau password salah")
    return render_template("login.html")



@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))



@app.route("/daftar", methods=["GET", "POST"])
def daftar():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        nama = request.form.get("nama")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            return render_template("daftar.html", error="Password tidak cocok")

        existing_user = User.query.filter_by(user_id=user_id).first()
        if existing_user:
            return render_template("daftar.html", error="User ID sudah terdaftar")

        hashed_password = generate_password_hash(password)
        new_user = User(user_id=user_id, nama=nama, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))
    return render_template("daftar.html")


@app.route("/quiz", methods=["GET", "POST"])
def quiz_page():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.filter_by(user_id=session["user_id"]).first()
    result = None

    if "remaining_questions" not in session:
        init_quiz()

    if request.method == "POST":
        selected = request.form.get("option")
        quiz = session.get("current_question")

        if quiz:
            user.quiz_answered += 1

            if selected == quiz["answer"]:
                user.quiz_correct += 1
                user.quiz_score += 10
                
                result = "Correct! 🎉"
            else:
                result = f"Wrong 😢. Jawaban benar: {quiz['answer']}"
            user.total_score = user.quiz_score
            db.session.commit()

    quiz = get_next_question()
    if quiz is None or user.quiz_answered >= MAX_QUESTIONS:
        return redirect(url_for("result"))

    return render_template(
        "quiz.html",
        quiz=quiz,
        result=result,
        user=user,
        max_q=MAX_QUESTIONS
    )


@app.route("/result")
def result():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.filter_by(user_id=session["user_id"]).first()
    percentage = (user.quiz_correct / user.quiz_answered * 100) if user.quiz_answered > 0 else 0

    return render_template(
        "result.html",
        user=user,
        percentage=percentage
    )



@app.route("/leaderboard")
def leaderboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    users = User.query.order_by(User.total_score.desc()).all()
    leaderboard_data = [{"name": u.user_id, "score": u.total_score} for u in users]

    return render_template("leaderboard.html", leaderboard=leaderboard_data)



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
