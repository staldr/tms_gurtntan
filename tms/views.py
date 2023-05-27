import csv
from flask import Flask, redirect, render_template, request, flash, session, url_for
from .models import *
import json
from werkzeug.utils import secure_filename
app = Flask(__name__)
app.secret_key = 'b7798833c2ffc6508de300553c40db2318b08d5b8f17ca08fafd5a8ede6e3dd6'
salt = bcrypt.gensalt()


@app.route("/")
def index():
    return redirect(url_for("explore"))

@app.route("/admin")
def admin():
    if session['admin']:
        check_tags = get_similar_tags()
        all_tags = get_tags()
        return render_template("admin.html", check_tags=check_tags, all_tags=all_tags)
    else:
        abort(403)

@app.route("/register", methods=["POST","GET"])
def register():
    if request.method == "POST":
        
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        phone = request.form["phone"]
        job_title = request.form["job_title"]
        password = bcrypt.hashpw(request.form["password"].encode('utf-8'), salt)
        create_person(first_name, last_name, email, phone, job_title)
        response = register_user(first_name, last_name, email, phone, job_title, password)

        if response == False:
            flash("Email address already exists.")
            return render_template("register.html")
        elif response == True:
            flash("Successfully registrated. Please log in.")
            return redirect(url_for("login")) 
        else:
            return "Wrong"
        
    elif request.method == "GET":
        return render_template("register.html")
    
@app.route("/login", methods=["POST","GET"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"].encode('utf-8')
        record = check_login(email,password)

        if record:
            if bcrypt.checkpw(password, record['u.password']):
                session['user'] = email
                if record['u.is_admin'] == True:
                    session['admin'] = True
                else:
                    session['admin'] = False
                return redirect(url_for("person", email=session['user']))
            else:
                flash("Invalid password.")
                return redirect(url_for("login"))
        else:
                flash("User does not exist.") 
                return redirect(url_for("login"))
    
    elif request.method == "GET":
        if "user" in session:
            return redirect(url_for("person", email=session['user']))
        
        return render_template("login.html")

@app.route("/people", methods=["GET", "POST"])
def people():
    search = request.form.get('search', '')
    if search:
        persons = find_persons_by_search(search.lower().strip())
    else:
        persons = get_persons()

    return render_template("persons.html", persons=persons, search=search)

@app.route("/persons/<email>")
def person(email):
    email = email
    is_user=False
    if "user" in session:
        if not email:
            email = session['user']
        if session['user'] == email:
            is_user=True

    result = find_person_by_email(email)
    person = dict(result)
    tags = find_tags_by_email(email)
    tasks = find_tasks_by_email(email)
    skills = find_skills_by_email(email)
    transfers = find_transfer_by_email(email)
    all_persons = get_persons()
    all_tags = get_tags()
    
    shared_skills = dict()
    count_skills = dict()
    endorsed_skill = dict()
    for skill in skills:
        tag = skill['t'].get('name')
        elementid = skill['elementid(s)']
        count = get_count_endorsements_by_skill(elementid)
        persons = find_person_with_shared_skills_by_email(tag,email)
        shared_skills[tag] = persons
        endorsed_skill[tag] = find_person_who_endorsed_by_skill(elementid)
        count_skills[elementid] = count

    tags_tasks = dict()       
    shared_tasks = dict()
    for task in tasks:
        elementid = task['elementid(t)']
        persons = find_persons_by_taskid(elementid)
        shared_tasks[elementid] = persons
        tags_s = find_tags_by_taskid(elementid)
        tags_tasks[elementid] = tags_s

    return render_template("person.html", all_tags=all_tags, endorsed_skill=endorsed_skill,all_persons=all_persons,transfers=transfers, person=person, tags=tags, tasks=tasks,skills=skills, shared_skills=shared_skills,shared_tasks=shared_tasks,tags_tasks=tags_tasks, is_user=is_user, count_skills=count_skills)

@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("admin", None)
    return redirect(url_for("login"))

@app.route("/explore")
def explore():
    limit = 5

    followed_tags = get_popular_tags("is_interested_in")
    worked_on_tags = get_popular_tags("works_on")
    common_skills = get_popular_tags("has")
    recently_added_tags = get_recently_added_tags() 
    transfers = get_transfer()
    transfer_tag_count = get_transfer_tag_count(limit)

    top_transferor = get_top_transferor(limit)
    top_skilled = get_top_skilled(limit)
    top_working = get_top_working(limit)

    ongoing_task = get_ongoing_task()

    tags_tasks = dict()       
    shared_tasks = dict()
    for task in ongoing_task:
        elementid = task['elementid(t)']
        persons = find_persons_by_taskid(elementid)
        shared_tasks[elementid] = persons
        tags_s = find_tags_by_taskid(elementid)
        tags_tasks[elementid] = tags_s

    return render_template("explore.html", tags_tasks=tags_tasks,shared_tasks=shared_tasks,ongoing_task=ongoing_task, top_working=top_working, top_skilled=top_skilled, top_transferor=top_transferor, transfer_tag_count=transfer_tag_count, recently_added_tags=recently_added_tags, transfers=transfers, followed_tags=followed_tags,worked_on_tags=worked_on_tags,common_skills=common_skills)

@app.route("/add_tag", methods=["POST"])
def add_tag():
    email = session['user']
    rel_type = request.args.get('rel_type')

    if rel_type == "create_single":
        tag = request.form.get("singletag")
        result = create_tag(tag)
        if result == True:
            flash("Tag successfully created.")
            return redirect(request.referrer)
        else:
            flash("Tag already exists.")
            return redirect(request.referrer)
    elif rel_type == "create_multiple":
        tags = []
        file = request.files['file']
        if file and file.filename.endswith('.txt'):
            filename = secure_filename(file.filename)
            file.save(filename)

            with open(filename, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    for elem in row:
                        tags.append(elem)
            
            total = len(tags)
            counter = 0
            for tag in tags:
                result = create_tag(tag)
                if result == True:
                    counter += 1           

            msg = str(counter) + "/" + str(total) + " Tag(s) successfully created. " + str(total-counter) + " Tag(s) already existed."
            flash(msg)
            return redirect(request.referrer)

    else:
        tags = []
        tags.append(request.form["tag"].lower().strip())


    if request.method == "POST":
        for tag in tags:
            add_tag_by_reltype(tag, email, rel_type)   

        return redirect(request.referrer)
        
@app.route("/remove_tag", methods=["POST"])
def remove_tag():
    rel_type = request.args.get('rel_type')
    email = session['user']
    if rel_type == "is_interested_in":
        checked_values = []
       
        for key in request.form:
            if key.startswith('checkbox_') and request.form.get(key) == 'on':
                checked_values.append(key.replace('checkbox_', ''))
        if not checked_values:
            checked_values.append(request.form["tag"].lower().strip())
    else:
        tag = request.form["tag"].lower().strip()

    if rel_type == "is_interested_in":
        remove_interest(tag,email,checked_values)
    
    return redirect(request.referrer)
        
@app.route("/remove_skill", methods=["POST"])
def remove_skill():
    email = session['user']
    tag = request.args.get('tag')
    remove_skill_by_tag(tag,email)

    return redirect(request.referrer)
    
@app.route("/add_skill", methods=["POST"])
def add_skill():
    email = session['user']
    tag = request.form["tag"].lower()
    desc = request.form["desc"]
    create_skill(tag,desc,email)

    return redirect(request.referrer)
    
@app.route("/add_task", methods=["POST"])
def add_task():
    email = session['user']
    desc = request.form["desc"]
    title = request.form["title"]
    start_date = request.form["start_date"]
    end_date = request.form["end_date"]
    collaborators = request.form.getlist("collaborators")
    tags = request.form.getlist("tags")

    create_task(desc, title, start_date, end_date, email,  tags, collaborators)

    return redirect(request.referrer)
    
@app.route("/add_transfer", methods=["POST"])
def add_transfer():
    p_from = request.form["from"]
    p_to = request.form["to"]
    tag = request.form["tag"].lower().strip()
    date = request.form["date"]
    create_transfer(p_from,p_to,tag,date)

    return redirect(request.referrer)

    
@app.route("/endorse_skill", methods=["POST"])
def endorse_skill():
    email = session['user']
    elementid = request.args.get('elementid')
    create_endorsement(elementid,email)

    return redirect(request.referrer)

@app.route("/tags", methods=["GET", "POST"])
def tags():
    search = request.form.get('search', '')
    if search:
        tags = find_tags_by_search(search.strip())
    else:
        tags = get_tags()

    return render_template("tags.html", tags=tags, search=search)

@app.route('/tags/<name>')
def tag(name):
    try:
        tag = find_tag_by_name(name)
    except:
        abort(404)
    
    all_persons = get_persons()
    followed_tags_other = find_connected_tags_by_name(name, "is_interested_in")
    skilled_tags_other = find_connected_tags_by_name(name, "skilled")
    helped_tags_other = find_connected_tags_by_name(name, "helped")
    worked_tags_other = find_connected_tags_by_name(name, "worked")
    related_tags = find_related_tags_by_name(name)

    persons_following = find_person_by_tag(name,"is_interested_in")

    follows = False
    if "user" in session:
        for person in persons_following:
            if person['p']['email'] == session['user']:
                follows = True

    persons_skilled = find_person_by_tag(name,"has")
    skilled = False
    if "user" in session:
        for person in persons_skilled:
            if person['p']['email'] == session['user']:
                skilled = True

    tasks = find_task_by_tag(name)
    transfers = get_transferorCount_by_tag(name)

    tags_tasks = dict()       
    shared_tasks = dict()
    for task in tasks:
        elementid = task['elementid(t)']
        persons = find_persons_by_taskid(elementid)
        shared_tasks[elementid] = persons
        tags_s = find_tags_by_taskid(elementid)
        tags_tasks[elementid] = tags_s

    return render_template("tag.html",  related_tags=related_tags, all_persons=all_persons, skilled=skilled, follows=follows, worked_tags_other=worked_tags_other,helped_tags_other=helped_tags_other, skilled_tags_other=skilled_tags_other, followed_tags_other=followed_tags_other, transfers=transfers, tag=tag, persons_following=persons_following,persons_skilled=persons_skilled,tasks=tasks,tags_tasks=tags_tasks,shared_tasks=shared_tasks)


@app.errorhandler(Exception)
def page_not_found(error):
    try:
        status_code = error.code
        msg = error.description
    except:
        raise error
    return render_template('error.html', status_code=status_code, msg=msg)

@app.route("/admin_tags", methods=["POST"])
def admin_tags():
    if session['admin']:
        action = request.args.get('action')
        tag1 = request.form["tag1"]
        tag2 = request.form["tag2"]

        if action == "relate":
            relate_tags(tag1,tag2)
            flash("Action successfully performed.")
            return redirect(url_for("admin"))
        elif action == "merge":
            merge_tags(tag1,tag2)
            flash("Action successfully performed.")
            return redirect(url_for("admin"))
    else:
        abort(403)