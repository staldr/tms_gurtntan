import bcrypt
from flask import Flask, jsonify, render_template, request, flash
from .models import Person, User

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
            flash("Successfully registrated.")
            return render_template("login.html")
        
    elif request.method == "GET":
        return render_template("register.html")
    
@app.route("/login", methods=["POST","GET"])
def login():
    if request.method == "POST":
        
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        phone = request.form["phone"]
        job_title = request.form["job_title"]
            
        person = Person(first_name, last_name, email, phone, job_title)

        response = person.create_person(person)
        if response == False:
            flash("E-Mail already exists.")
            return render_template("register.html")
        else:
            flash("Successfully registrated.")
            return render_template("login.html")
        
    elif request.method == "GET":
        return render_template("login.html")

    



