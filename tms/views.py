import csv
import bcrypt
from flask import Flask, jsonify, redirect, render_template, request, flash, session, url_for
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

        response = register_user(first_name, last_name, email, phone, job_title, password)

        if response == False:
            flash("Email address already exists.")
            return render_template("register.html")
        else:
            flash("Successfully registrated. Please log in.")
            return redirect(url_for("login")) 
        
    elif request.method == "GET":
        return render_template("register.html")
    
@app.route("/login", methods=["POST","GET"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"].encode('utf-8')
                                                    
        with tms_db.session() as tx:
            result = tx.run("MATCH (u:user) where u.email = $email return u.password, u.is_admin", email=email)
            record = result.single()
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

    #return persons
    return render_template("person.html", all_tags=all_tags, endorsed_skill=endorsed_skill,all_persons=all_persons,transfers=transfers, person=person, tags=tags, tasks=tasks,skills=skills, shared_skills=shared_skills,shared_tasks=shared_tasks,tags_tasks=tags_tasks, is_user=is_user, count_skills=count_skills)

@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("admin", None)
    return redirect(url_for("login"))

@app.route("/explore")
def explore():
    followed_tags = get_popular_tags("follows")
    worked_on_tags = get_popular_tags("works_on")
    common_skills = get_popular_tags("has")
    #uncommon_skills = get_unpopular_tags("has")
    recently_added_tags = get_recently_added_tags() 
    transfers = get_transfer()
    transfer_tag_count = get_transfer_tag_count()
    return render_template("explore.html", transfer_tag_count=transfer_tag_count, recently_added_tags=recently_added_tags, transfers=transfers, followed_tags=followed_tags,worked_on_tags=worked_on_tags,common_skills=common_skills)

@app.route("/add_tag", methods=["POST"])
def add_tag():
    email = session['user']
    rel_type = request.args.get('rel_type')
    '''
    if rel_type == "follows_multiple":
        tags = request.form.getlist("tags")
        tags.append(request.form.get("singletag"))
        rel_type = "follows"
    '''
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
                for tag in tags:
                    tx.run(query, tag=tag, email=email)
            except:
                return abort(500) # TODO: Exception Handling ausbauen
            return redirect(request.referrer)
        
@app.route("/remove_tag", methods=["POST"])
def remove_tag():
    rel_type = request.args.get('rel_type')
    email = session['user']
    if rel_type == "follows":
        checked_values = []
       
        for key in request.form:
            if key.startswith('checkbox_') and request.form.get(key) == 'on':
                checked_values.append(key.replace('checkbox_', ''))
        if not checked_values:
            checked_values.append(request.form["tag"].lower().strip())
    else:
        tag = request.form["tag"].lower().strip()

        
    if request.method == "POST":
        with tms_db.session() as tx:
            if rel_type == "follows":
                query = "match (t:tag)<-[r:{}]-(p:person) where t.name = $tag and p.email = $email delete r".format(rel_type)
                for tag in checked_values:
                    try:        
                        tx.run(query, tag=tag, email=email)
                    except:
                        return abort(500) # TODO: Exception Handling ausbauen
            elif rel_type == "has":
                query = "match (t:tag)<-[r1:includes]-(s:skill)<-[r2:has]-(p:person) where t.name = $tag and p.email = $email delete r1, r2, s"
                tx.run(query, tag=tag, email=email)
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
    #tag = request.form["tag"].lower()
    tag = request.form["tag"].lower()
    desc = request.form["desc"]
    query = '''
        MERGE (t:tag {name: $tag})
        ON CREATE SET t.created = datetime(), t.last_modified = datetime()
        MERGE (s:skill {description: $desc})
        ON CREATE SET s.created = datetime(), s.last_modified = datetime()
        with s,t
        MATCH (p:person) WHERE p.email = $email
        MERGE (p)-[:has]->(s)-[:includes]->(t)
    '''
    if request.method == "POST":
        with tms_db.session() as tx:
            tx.run(query, tag=tag, desc=desc, email=email)
        return redirect(request.referrer)
    
@app.route("/add_task", methods=["POST"])
def add_task():
    email = session['user']
    desc = request.form["desc"]
    title = request.form["title"]
    start_date = request.form["start_date"]
    end_date = request.form["end_date"]
    '''
    tags_string = request.form["tag"].lower()
    tags = set(tags_string.split(";")) 
    '''
    collaborators = request.form.getlist("collaborators")
    tags = request.form.getlist("tags")

    query = '''
        CREATE (t:task {created: datetime(), last_modified: datetime(), description: $desc, title: $title, start_date: $start_date, end_date: $end_date}) WITH t
        MATCH (p:person) WHERE p.email = $email
        CREATE (p)-[:works_on]->(t)
        RETURN elementid(t) as elementid
    '''
    query2 = '''
        MATCH (t:task), (p:person) WHERE elementid(t) = $elementid and p.email = $collaborator
        CREATE (p)-[:works_on]->(t) 
    '''
    query3 = '''
        merge (tag:tag {name: $tag})
        ON CREATE SET tag.created = datetime(), tag.last_modified = datetime()
        with tag
        MATCH (t:task) WHERE elementid(t) = $elementid
        CREATE (t)-[:includes]->(tag)
    '''
    with tms_db.session() as tx:
        result = tx.run(query, desc=desc, title=title, start_date=start_date, end_date=end_date, email=email)
        elementid = result.single()["elementid"]
        for collaborator in  collaborators:
            tx.run(query2, collaborator=collaborator, elementid=elementid)
        for tag in tags:
            tx.run(query3, tag=tag, elementid=elementid)

    return redirect(request.referrer)
    
@app.route("/add_transfer", methods=["POST"])
def add_transfer():
    p_from = request.form["from"]
    p_to = request.form["to"]
    tag = request.form["tag"].lower().strip()
    date = request.form["date"]
    query = '''
        merge (t:tag {name: $tag})
        ON CREATE SET t.created = datetime(), t.last_modified = datetime()
        with t
        match (p_to:person) where p_to.email = $p_to
        match (p_from:person) where p_from.email = $p_from
        create (tx:transfer {date: $date, created: datetime(), last_modified: datetime()})
        create (p_to)<-[:to]-(tx)<-[:from]-(p_from)
        create (tx)-[:includes]->(t)
        return tx
    '''
    if request.method == "POST":
        with tms_db.session() as tx:
            tx.run(query, p_from=p_from, p_to=p_to, tag=tag, date=date)
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
    with tms_db.session() as tx:
        try:        
            tx.run(query, elementid=elementid, email=email)
        except:
            return abort(500) # TODO: Exception Handling ausbauen
    return redirect(request.referrer)

@app.route("/tags", methods=["GET", "POST"])
def tags():
    search = request.form.get('search', '')
    if search:
        tags = find_tags_by_search(search.lower().strip())
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
    followed_tags_other = find_connected_tags_by_name(name, "follows")
    skilled_tags_other = find_connected_tags_by_name(name, "skilled")
    helped_tags_other = find_connected_tags_by_name(name, "helped")
    worked_tags_other = find_connected_tags_by_name(name, "worked")
    related_tags = find_related_tags_by_name(name)

    persons_following = find_person_by_tag(name,"follows")

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
    transfers = find_frequent_transfer_by_tag(name)

    tags_tasks = dict()       
    shared_tasks = dict()
    for task in tasks:
        elementid = task['elementid(t)']
        persons = find_persons_by_taskid(elementid)
        shared_tasks[elementid] = persons
        tags_s = find_tags_by_taskid(elementid)
        tags_tasks[elementid] = tags_s

    return render_template("tag.html",  related_tags=related_tags, all_persons=all_persons, skilled=skilled, follows=follows, worked_tags_other=worked_tags_other,helped_tags_other=helped_tags_other, skilled_tags_other=skilled_tags_other, followed_tags_other=followed_tags_other, transfers=transfers, tag=tag, persons_following=persons_following,persons_skilled=persons_skilled,tasks=tasks,tags_tasks=tags_tasks,shared_tasks=shared_tasks)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

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