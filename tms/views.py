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

    
@app.route("/person/")
def person():
    email = request.args.get('email')
    
    is_user=False
    if "user" in session:
        if session['user'] == email:
            is_user=True

    result = find_person_by_email(email)
    person = dict(result)
    tags = find_tags_by_email(email)
    tasks = find_tasks_by_email(email)
    skills = find_skills_by_email(email)
    
    shared_skills = dict()
    count_skills = dict()
    for skill in skills:
        tag = skill['t'].get('name')
        elementid = skill['elementid(s)']
        count = get_count_endorsements_by_skill(elementid)
        persons = find_person_with_shared_skills_by_email(tag,email)
        shared_skills[tag] = persons
        count_skills[elementid] = count

    tags_tasks = dict()       
    shared_tasks = dict()
    for task in tasks:
        elementid = task['elementid(t)']
        persons = find_persons_by_taskid(elementid)
        shared_tasks[elementid] = persons
        tags_s = find_tags_by_taskid(elementid)
        tags_tasks[elementid] = tags_s

    return render_template("person.html", person=person, tags=tags, tasks=tasks,skills=skills, shared_skills=shared_skills,shared_tasks=shared_tasks,tags_tasks=tags_tasks, is_user=is_user, count_skills=count_skills)

'''
@app.route("/user/shared-skills/<tag>")  
def shared_skills(tag):
    tag = tag
    email = "anneliese.braun@gmail.com"
    persons = find_person_with_shared_skills_by_email(tag,email)
    return render_template("shared-skills.html", persons=persons, tag=tag)
'''


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/explore")
def explore():
    return render_template("explore.html")

@app.route("/add_tag", methods=["POST","GET"])
def add_tag():
    email = session['user']
    tag = request.form["tag"]
    rel_type = request.args.get('rel_type')
    query = '''merge (t:tag {{name: $tag}})
                                    ON CREATE SET t.created = datetime(), t.last_modified = datetime()
                                    with t
                                    match (p:person) where p.email = $email
                                    merge (p)-[r:{}]->(t)
                                    ON CREATE SET r.created = datetime()
                                    '''.format(rel_type)
    if request.method == "POST":
        with tms_db.session() as tx:
            try:
                tx.run(query, tag=tag, email=email)
            except:
                return abort(500) # TODO: Exception Handling ausbauen
            return redirect(request.referrer)
        
@app.route("/remove_tag", methods=["POST"])
def remove_tag():
    email = session['user']
    checked_values = []
    rel_type = request.args.get('rel_type')
    query = "match (t:tag)<-[r:{}]-(p:person) where t.name = $tag and p.email = $email delete r,t".format(rel_type)
    for key in request.form:
        if key.startswith('checkbox_') and request.form.get(key) == 'on':
            checked_values.append(key.replace('checkbox_', ''))
    if request.method == "POST":
        with tms_db.session() as tx:
            for tag in checked_values:
                try:        
                    tx.run(query, tag=tag, email=email)
                except:
                    return abort(500) # TODO: Exception Handling ausbauen
            return redirect(request.referrer)
        
@app.route("/remove_skill", methods=["POST"])
def remove_skill():
    email = session['user']
    tag = request.args.get('tag')
    query = "match (t:tag)<-[r1:includes]-(s:skill)<-[r2:has]-(p:person) where t.name = $tag and p.email = $email delete r1,s,r2"
    if request.method == "POST":
        with tms_db.session() as tx:
            try:        
                tx.run(query, tag=tag, email=email)
            except:
                return abort(500) # TODO: Exception Handling ausbauen
        return redirect(request.referrer)
    
@app.route("/add_skill", methods=["POST"])
def add_skill():
    email = session['user']
    tag = request.form["tag"]
    desc = request.form["desc"]
    query = '''
        merge (t:tag {name: $tag})
        ON CREATE SET t.created = datetime(), t.last_modified = datetime()
        merge (s:skill {description: $desc})
        ON CREATE SET s.created = datetime(), s.last_modified = datetime()
        with s,t
        match (p:person) where p.email = $email
        merge (p)-[r:has]->(s)-[r2:includes]->(t)
        ON CREATE SET r.created = datetime()
    '''
    if request.method == "POST":
        with tms_db.session() as tx:
            try:        
                tx.run(query, tag=tag, desc=desc, email=email)
            except:
                return abort(500) # TODO: Exception Handling ausbauen
        return redirect(request.referrer)
    
@app.route("/endorse_skill", methods=["POST"])
def endorse_skill():
    if "user" not in session:
        pass
        # TODO if users are not logged in flash message or don't show button at all. (handle in html)

    email = session['user']
    elementid = request.args.get('elementid')
    query = '''
        match (s:skill), (p:person)
        where elementid(s) = $elementid and p.email = $email
        merge (p)-[r:endorses]->(s)
        ON CREATE SET r.created = datetime()
    '''
    if request.method == "POST":
        with tms_db.session() as tx:
            try:        
                tx.run(query, elementid=elementid, email=email)
            except:
                return abort(500) # TODO: Exception Handling ausbauen
        return redirect(request.referrer)
