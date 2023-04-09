import bcrypt
from flask import Flask, jsonify, redirect, render_template, request, flash, session, url_for
from .models import *
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
salt = bcrypt.gensalt()


@app.route("/")
def index():
    return render_template("index.html", message="Hello World")

@app.route("/register", methods=["POST","GET"])
def register():
    if request.method == "POST":
        
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        phone = request.form["phone"]
        job_title = request.form["job_title"]
        password = bcrypt.hashpw(request.form["password"].encode('utf-8'), salt)

        user = User(first_name, last_name, email, phone, job_title, password)

        response = user.register(user)
        if response == False:
            flash("E-Mail already exists.")
            return render_template("register.html")
        else:
            flash("Successfully registrated. Please log in.")
            return render_template("login.html")
        
    elif request.method == "GET":
        return render_template("register.html")
    
@app.route("/login", methods=["POST","GET"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"].encode('utf-8')
                                                    
        with tms_db.session() as tx:
            result = tx.run("MATCH (u:user) where u.email = $email return u.password, u.email", email=email)
            record = result.single()
            if record:
                if bcrypt.checkpw(password, record['u.password']):
                    session['user'] = email
                    return redirect(url_for("user"))
                else:
                    flash("Invalid password.")
                    return redirect(url_for("login"))
            else:
                    flash("User does not exist.") 
                    return redirect(url_for("login"))
        
    elif request.method == "GET":
        if "user" in session:
            return redirect(url_for("user"))
        
        return render_template("login.html")
    
@app.route("/user")
def user():
    if "user" in session:
        result = find_person_by_email(session['user'])
        user = dict(result)
        tags = find_tags_by_email(session['user'])
        tasks = find_tasks_by_email(session['user'])
        skills = find_skills_by_email(session['user'])
        
        shared_skills = dict()
        for skill in skills:
            tag = skill['t'].get('name')
            persons = find_person_with_shared_skills_by_email(tag,session['user'])
            shared_skills[tag] = persons

        tags_tasks = dict()       
        shared_tasks = dict()
        for task in tasks:
            elementid = task['elementid(t)']
            persons = find_persons_by_taskid(elementid)
            shared_tasks[elementid] = persons
            tags_s = find_tags_by_taskid(elementid)
            tags_tasks[elementid] = tags_s

        return render_template("user.html", user=user, tags=tags, tasks=tasks,skills=skills, shared_skills=shared_skills,shared_tasks=shared_tasks,tags_tasks=tags_tasks)
    else:
        flash("Please log in.")
        return redirect(url_for("login"))

@app.route("/user/shared-skills/<tag>")  
def shared_skills(tag):
    tag = tag
    email = "anneliese.braun@gmail.com"
    persons = find_person_with_shared_skills_by_email(tag,email)
    return render_template("shared-skills.html", persons=persons, tag=tag)



@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/explore")
def explore():
    return render_template("explore.html")

