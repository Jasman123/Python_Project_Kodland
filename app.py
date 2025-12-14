from flask import Flask, render_template, request
import requests
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask import redirect, url_for, flash
now = datetime.now()
import os

app = Flask(__name__)
app.secret_key = "super-secret-key-123"
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), unique=True, nullable=False)
    nama = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)

API_KEY = "0387275c79394f1892c142747251312"
BASE_URL = "http://api.weatherapi.com/v1"

with app.app_context():
    db.create_all()
    print("sucessfully created")

quiz = {
    "question": "What is the capital of France?",
    "options": ["Berlin", "Madrid", "Paris", "Rome"],
    "answer": "Paris"
}


@app.route("/", methods=["GET", "POST"])
def home():
    data_cuaca = None
    now = datetime.now()
    today = now.strftime("%A, %d %B %Y %H:%M:%S")

    if request.method == "POST":
        kota = request.form.get("kota")

        response = requests.get(
            f"{BASE_URL}/forecast.json",
            params={
                "key": API_KEY,
                "q": kota,
                "days": 3
            }
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

            hari = {

            }


    return render_template("home.html", cuaca=data_cuaca, today=today)

from flask import session

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        password = request.form.get("password")

        user = User.query.filter_by(user_id=user_id).first()

        if user and check_password_hash(user.password, password):
            # SIMPAN LOGIN KE SESSION
            session["user_id"] = user.user_id
            session["nama"] = user.nama

            print("succesffuly login")
            return redirect(url_for("home"))

        else:
            return render_template("login.html", error="User ID atau password salah")

    return render_template("login.html")


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

        new_user = User(
            user_id=user_id,
            nama=nama,
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("daftar.html")



@app.route("/quiz", methods=["GET", "POST"])
def quiz_page():
    result = None
    if request.method == "POST":
        selected = request.form.get("option")
        result = "Correct! 🎉" if selected == quiz["answer"] else f"Wrong 😢. The correct answer is {quiz['answer']}."
    return render_template("quiz.html", quiz=quiz, result=result)

@app.route("/leaderboard")
def leaderboard():
    leaderboard_data = [
        {"name": "Alice", "score": 150},
        {"name": "Bob", "score": 120},
        {"name": "Charlie", "score": 100},
    ]
    return render_template("leaderboard.html", leaderboard=leaderboard_data)



if __name__ == "__main__":
    app.run(debug=True)
