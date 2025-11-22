from flask import Flask, redirect, render_template, request, session
from joblib import load
import numpy as np
from cs50 import SQL
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from functions import login_required

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///dahacks.db")
model = load("stress_model.pkl")
@app.route("/home")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm  = request.form.get("confirmpassword")

        if not username:
            warning = "Sorry, you didn't type the username in the username field. Ensure you type the username."
            return render_template("error.html", warning=warning)

        if not password:
            warning = "Sorry, you didn't type the password in the password field. Ensure to type the password."
            return render_template("error.html", warning=warning)

        if password != confirm:
            warning = "Sorry, the confirmation password you typed in doesn't match with the password. Ensure that both match each other."
            return render_template("error.html", warning=warning)

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) == 1:
            warning = "Sorry, the username you typed in already exists. Please type in another username."
            return render_template("error.html", warning=warning)

        hash = generate_password_hash(password)
        db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", username, hash)

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        session["user_id"] = rows[0]["user_id"] 

        return redirect("/")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    session.clear()

    if request.method == "POST":

        if not request.form.get("username"):
            warning = "Sorry, you didn't type the username in the username field. Ensure you type the username."
            return render_template("error.html", warning = warning)


        elif not request.form.get("password"):
            warning = "Sorry, you didn't type the password in the password field. Ensure to type the password."
            return render_template("error.html", warning = warning)


        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )


        if len(rows) != 1 or not check_password_hash(
            rows[0]["password_hash"], request.form.get("password")
        ):
            warning = "Sorry, either the username doesn't exist or the password associated with that username is invalid"
            return render_template("error.html", warning = warning)

        session["user_id"] = rows[0]["user_id"]

        return redirect("/")
    return render_template("login.html")

@app.route("/error")
def error_page():
    return render_template("error.html")

@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/dashboard")
@login_required
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    rows = db.execute(
        """
        SELECT 
            sleep_hours, 
            exercise_hours, 
            study_hours, 
            work_hours, 
            stress_level,
            strftime('%Y-%m-%d', created_at) AS date_only
        FROM stress_entries
        WHERE user_id = ?
        ORDER BY entry_id DESC
        LIMIT 7
        """,
        user_id
    )

    return render_template("dashboard.html", entries=rows)


@app.route("/analytics", methods=["GET", "POST"])
@login_required
def analytics_page():
    if request.method == "POST":
        try:
            work_hours = float(request.form.get("workHours", 0))
            study_hours = float(request.form.get("studyHours", 0))
            sleep_duration = float(request.form.get("sleepHours", 0))
            exercise = float(request.form.get("exerciseHours", 0))
        except ValueError:
            warning = "Analytics input values are invalid."
            return render_template("error.html", warning=warning)

        # ---- PERCENTAGE CALCULATIONS ----

        # Sleep: 7–9 hours = 100% (optimal), less or more sleep = lower percentage
        if sleep_duration < 7:
            sleep_percentage = (sleep_duration / 7) * 100  # Scale 0–7 hours as 0%–100%
        elif sleep_duration <= 9:
            sleep_percentage = 100  # 7–9 hours = optimal
        else:
            sleep_percentage = max(100 - ((sleep_duration - 9) * 5), 0)  # Reduce 5% for every hour above 9

        # Exercise: 1–2 hours = 100% (optimal), less or more exercise = lower percentage
        if exercise < 1:
            exercise_percentage = (exercise / 1) * 50  # Scale 0–1 hours as 0%–50%
        elif exercise <= 2:
            exercise_percentage = 50 + ((exercise - 1) / 1) * 50  # Scale 1–2 hours as 50%–100%
        else:
            exercise_percentage = max(100 - ((exercise - 2) * 20), 0)  # Reduce 20% for every hour above 2

        # Study: 2–4 hours = 100% (optimal), less or more study = lower percentage
        if study_hours < 2:
            study_percentage = (study_hours / 2) * 50  # Scale 0–2 hours as 0%–50%
        elif study_hours <= 4:
            study_percentage = 50 + ((study_hours - 2) / 2) * 50  # Scale 2–4 hours as 50%–100%
        else:
            study_percentage = max(100 - ((study_hours - 4) * 15), 0)  # Reduce 15% for every hour above 4

        # Work: 1–2 hours = 100% (peak efficiency), 3–4 hours = moderate efficiency, 5–6 hours = noticeable drop, 7–9 hours = poor efficiency, 9+ hours = 0%
        if work_hours < 1:
            work_percentage = (work_hours / 1) * 50  # Scale 0–1 hours as 0%–50%
        elif work_hours <= 2:
            work_percentage = 50 + ((work_hours - 1) / 1) * 50  # Scale 1–2 hours as 50%–100%
        elif work_hours <= 4:
            work_percentage = 100 - ((work_hours - 2) / 2) * 25  # Scale 2–4 hours as 100%–75%
        elif work_hours <= 6:
            work_percentage = 75 - ((work_hours - 4) / 2) * 35  # Scale 4–6 hours as 75%–40%
        elif work_hours <= 9:
            work_percentage = 40 - ((work_hours - 6) / 3) * 40  # Scale 6–9 hours as 40%–0%
        else:
            work_percentage = 0  # 9+ hours = 0%

        # ---- SLEEP FEEDBACK ----
        if sleep_duration <= 4:
            sleep_msg = (
                f"You reported {sleep_duration} hours of sleep. Very short sleep (<5 h) is associated with high stress, "
                "poor mood, and reduced cognitive performance. Try to increase sleep gradually.\n"
                "Sources: CDC, Harvard Medical School, APA"
            )
        elif sleep_duration <= 6:
            sleep_msg = (
                f"You reported {sleep_duration} hours of sleep. This is below the recommended 7–9 hours. "
                "Chronic sleep restriction can elevate stress and impair memory and concentration.\n"
                "Sources: CDC, APA"
            )
        elif sleep_duration <= 9:
            sleep_msg = (
                f"You reported {sleep_duration} hours of sleep. This is within the healthy range. "
                "Consistent sleep helps reduce stress and supports mental and physical health.\n"
                "Sources: Harvard Medical School, APA"
            )
        else:
            sleep_msg = (
                f"You reported {sleep_duration} hours of sleep. Oversleeping occasionally is fine, "
                "but regular long sleep (>9 h) may be linked to fatigue or disrupted circadian rhythms.\n"
                "Sources: APA"
            )

        # ---- EXERCISE FEEDBACK ----
        if exercise <= 0.5:
            exercise_msg = (
                f"You reported {exercise} hours of exercise. Minimal activity increases stress and fatigue. "
                "Even short daily activity can improve mood.\n"
                "Sources: PMC, Mayo Clinic"
            )
        elif exercise <= 1:
            exercise_msg = (
                f"You reported {exercise} hours of exercise. This is a healthy range that reduces stress and supports mental health.\n"
                "Sources: PMC, Mayo Clinic"
            )
        elif exercise <= 2.5:
            exercise_msg = (
                f"You reported {exercise} hours of exercise. Above-average activity improves mood and cardiovascular health, "
                "but ensure proper recovery.\n"
                "Sources: Nature, PMC"
            )
        else:
            exercise_msg = (
                f"You reported {exercise} hours of exercise. Excessive exercise without rest may increase stress and disrupt sleep.\n"
                "Sources: Nature, PMC"
            )

        # ---- STUDY FEEDBACK ----
        if study_hours <= 1:
            study_msg = (
                f"You reported {study_hours} hours of study. Light study may be okay for one day, "
                "but insufficient study over time can increase stress.\n"
                "Sources: Arxiv, ScienceDirect"
            )
        elif study_hours <= 3:
            study_msg = (
                f"You reported {study_hours} hours of study. Balanced study blocks with breaks support learning and reduce stress.\n"
                "Sources: ScienceDirect"
            )
        elif study_hours <= 5:
            study_msg = (
                f"You reported {study_hours} hours of study. Long sessions without breaks increase stress and fatigue. "
                "Take short breaks to improve retention.\n"
                "Sources: Arxiv, ScienceDirect"
            )
        else:
            study_msg = (
                f"You reported {study_hours} hours of study. Excessive study increases stress significantly. "
                "Use time management strategies and incorporate rest.\n"
                "Sources: Arxiv, ScienceDirect"
            )

        # ---- WORK FEEDBACK ----
        if work_hours <= 2:
            work_msg = (
                f"You reported {work_hours} hours of work. Short work periods are low stress.\n"
                "Sources: PMC, WHO/ILO"
            )
        elif work_hours <= 4:
            work_msg = (
                f"You reported {work_hours} hours of work. Moderate work hours are generally safe, but take short breaks.\n"
                "Sources: PMC"
            )
        elif work_hours <= 6:
            work_msg = (
                f"You reported {work_hours} hours of work. Long work periods can elevate stress and fatigue. "
                "Include breaks and avoid consecutive long days.\n"
                "Sources: PMC, PLOS ONE"
            )
        else:
            work_msg = (
                f"You reported {work_hours} hours of work. Extended work hours (>6h/day) are linked with higher stress, fatigue, and burnout risk. Prioritize recovery.\n"
                "Sources: PMC, WHO/ILO"
            )

        return render_template(
            "analytics.html",
            sleep_msg=sleep_msg,
            exercise_msg=exercise_msg,
            study_msg=study_msg,
            work_msg=work_msg,
            sleep_percentage=sleep_percentage,
            study_percentage=study_percentage,
            work_percentage=work_percentage,
            exercise_percentage=exercise_percentage,
        )
    else:
        return redirect("/")

@app.route("/predict", methods=["GET", "POST"])
@login_required
def predict():
    if request.method == "POST":
        work_hours = request.form.get("workHours", "")
        study_hours = request.form.get("studyHours", "")
        sleep_duration = request.form.get("sleepHours", "")
        exercise = request.form.get("exerciseHours", "")

        if not (work_hours and study_hours and sleep_duration and exercise):
            warning = "All the fields are empty"
            return render_template("error.html", warning = warning)
        
        if not work_hours:
            warning = "Work Hours field is empty!"
            return render_template("error.html", warning=warning)
        if not study_hours:
            warning = "Study Hours field is empty!"
            return render_template("error.html", warning=warning)
        if not sleep_duration:
            warning = "Sleep Duration field is empty!"
            return render_template("error.html", warning=warning)
        if not exercise:
            warning = "Exercise field is empty!"
            return render_template("error.html", warning=warning)
        
        try:
            work_hours = float(work_hours)
            study_hours = float(study_hours)
            sleep_duration = float(sleep_duration)
            exercise = float(exercise)
        except ValueError:
            warning = "All fields must be numbers!"
            return render_template("error.html", warning=warning)
        
        time = work_hours + study_hours + sleep_duration + exercise
        if time > 24.0:
            warning = "The time of the activities has exceeded 24 hours"
            return render_template("error.html", warning=warning)
        
        X = np.array([[work_hours, study_hours, sleep_duration, exercise]])
        stress_pred = model.predict(X)[0]
        stressValue = float(stress_pred)

        if stressValue < 0:
            stressValue = 0
        if stressValue > 10:
            stressValue = 10

        db.execute(
            "INSERT INTO stress_entries (user_id, sleep_hours, exercise_hours, study_hours, work_hours, stress_level) VALUES (?, ?, ?, ?, ?, ?)",
                session["user_id"],
                sleep_duration,
                exercise,
                study_hours,
                work_hours,
                stressValue
            )
        
        # ---- STRESS MESSAGE LOGIC ----
        if stressValue <= 1:
            msg = "You’re extremely relaxed — keep it up!"
        elif stressValue <= 2:
            msg = "Very low stress. You're doing great."
        elif stressValue <= 3:
            msg = "Low stress. Stay consistent with your healthy routine."
        elif stressValue <= 4:
            msg = "Mild stress. Nothing to worry about, but be mindful."
        elif stressValue <= 5:
            msg = "Moderate stress. Try to take breaks and rest."
        elif stressValue <= 6:
            msg = "Above average stress. Consider adjusting your schedule."
        elif stressValue <= 7:
            msg = "High stress. Please slow down and practice self-care."
        elif stressValue <= 8:
            msg = "Very high stress. You may need to decompress."
        elif stressValue <= 9:
            msg = "Severe stress. Talk to a friend or take time to breathe."
        else:  # stress == 10
            msg = "Extremely high stress. Please reach out for help and take time to rest."
              
        if stressValue < 4:
            colorClass = "low-stress"
        elif stressValue < 8:
            colorClass = "medium-stress"
        else:
            colorClass = "high-stress"
    
        return render_template("results.html", stress=round(stressValue, 2), message=msg, colorClass = colorClass, work_hours = work_hours, study_hours = study_hours, sleep_duration = sleep_duration, exercise = exercise)
    else:
        return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)