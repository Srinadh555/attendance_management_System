from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd
import os
from datetime import datetime, date, time

app = Flask(__name__)
app.secret_key = "your_secret_key"

USERS_FILE = "users.xlsx"
ATTENDANCE_FILE = "attendance.xlsx"



def init_excel():
    if not os.path.exists(USERS_FILE):
        pd.DataFrame(columns=["roll_no", "username", "password", "role","time","date"]).to_excel(
            USERS_FILE, index=False
        )
    if not os.path.exists(ATTENDANCE_FILE):
        pd.DataFrame(columns=["roll_no", "status", "time", "date"]).to_excel(
            ATTENDANCE_FILE, index=False
        )


def read_users():
    return pd.read_excel(USERS_FILE)


def write_users(df):
    df.to_excel(USERS_FILE, index=False)


def read_attendance():
    return pd.read_excel(ATTENDANCE_FILE)


def write_attendance(df):
    df.to_excel(ATTENDANCE_FILE, index=False)


@app.before_request
def before_request():
    init_excel()





@app.route("/", methods=["GET", "POST"])
def login():
   
    if request.method == "GET" and "username" in session:
        role = session.get("role", "").lower()
        if role == "student":
            return redirect(url_for("student_dashboard"))
        elif role == "staff":
            return redirect(url_for("staff_dashboard"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = read_users()

        user_row = users[
            (users["username"] == username) & (users["password"].astype(str) == str(password))
        ]

        if len(user_row) > 0:
            user = user_row.iloc[0]
            session["username"] = str(user["username"])
            session["role"] = str(user["role"])
            session["roll_no"] = str(user["roll_no"])

           
            if session["role"].lower() == "student":
                return redirect(url_for("student_dashboard"))
            else:
                return redirect(url_for("staff_dashboard"))
        else:
            flash("Invalid credentials")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        roll_no = request.form["roll_no"]
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]
        reg_time = datetime.now().strftime("%I:%M:%p")
        reg_date =date.today().isoformat()


        users = read_users()
        if username in users["username"].values:
            flash("Username already exists")
        else:
            new_user = pd.DataFrame(
                [
                    {
                        "roll_no": roll_no,
                        "username": username,
                        "password": password,
                        "role": role,
                        "reg_time": reg_time,
                        "reg_date": reg_date,
                        
                    }
                ]
            )
            updated_users = pd.concat([users, new_user], ignore_index=True)
            write_users(updated_users)
            flash("Registration successful. Login now.")
            return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/student")
def student_dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    if session.get("role", "").lower() != "student":
        return redirect(url_for("staff_dashboard"))

    roll_no = session["roll_no"]
    attendance = read_attendance()
    my_att = attendance[attendance["roll_no"].astype(str) == str(roll_no)]

    total = len(my_att)
    present = len(my_att[my_att["status"] == "Present"])
    absent = total - present
    rate = round((present / total * 100), 2) if total > 0 else 0

    return render_template(
        "student_dashboard.html",
        username=session["username"],
        roll_no=roll_no,
        records=my_att.to_dict("records"),
        total=total,
        present=present,
        absent=absent,
        rate=rate,
    )


@app.route("/staff", methods=["GET", "POST"])
def staff_dashboard():
    if "username" not in session or session.get("role") != "staff":
        return redirect(url_for("login"))

    users = read_users()
    students_df = users[users["role"] == "student"]
    attendance_df = read_attendance()

    if request.method == "POST":
       
        date_str = request.form.get("date", date.today().isoformat())
        current_time =datetime.now().strftime("%I:%M:%p")
        
        
        new_entries = []
        for _, stud in students_df.iterrows():
            
            roll = str(stud["roll_no"])
            
           
            status = "Present" if f"present_{roll}" in request.form else "Absent"
            
            new_entries.append({
                "roll_no": stud["roll_no"],  
                "status": status,
                "time" : current_time,
                "date": date_str,})

        if new_entries:
            new_df = pd.DataFrame(new_entries)
            updated_attendance = pd.concat([attendance_df, new_df], ignore_index=True)
            write_attendance(updated_attendance.drop_duplicates(subset=["date", "roll_no"],keep='last'))
            updated_attendance = updated_attendance.sort_values(by = ['date', 'roll_no'])
            write_attendance(updated_attendance)
            flash(f"Attendance saved for {date_str}!")
         
            attendance_df = updated_attendance

   
    summary_data = []
    for _, stud in students_df.iterrows():
       
        roll_val = str(stud["roll_no"])
        student_history = attendance_df[attendance_df["roll_no"].astype(str) == roll_val]
        
        total = len(student_history)
        present = len(student_history[student_history["status"] == "Present"])
        absent = total - present
        rate = round((present / total * 100), 2) if total > 0 else 0

        summary_data.append({
            "roll_no": stud["roll_no"],
            "name": stud["username"],
            "total": total,
            "present": present,
            "absent": absent,
            "rate": f"{rate}%"
        })

    return render_template(
        "staff_dashboard.html",
        username=session["username"],
        students=summary_data, 
        today=date.today().isoformat()
    )


if __name__ == "__main__":
    app.run(debug=True)
