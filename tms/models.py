# Classes and functions
from flask import abort
import bcrypt
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="tms/credentials-ff8b3a26.env")

url = os.environ.get('NEO4J_URI')
username = os.environ.get('NEO4J_USERNAME')
password = os.environ.get('NEO4J_PASSWORD')

tms_db = GraphDatabase.driver(url, auth=(username, password))

def create_person(first_name, last_name, email, phone, job_title):

        query = '''
        MERGE (p:person {
                first_name: $first_name
                ,last_name: $last_name
                ,email: $email
                ,phone: $phone
                ,job_title: $job_title
                ,created: datetime()
                ,last_modified: datetime()
                })
        RETURN p
        '''
        with tms_db.session() as session:
            try:
                result = session.run(query, first_name=first_name, last_name=last_name, email=email, phone=phone, job_title=job_title)
                return result
            except Exception as e:
                msg = str(e)
                abort(500, msg)

def create_user(first_name, last_name, email, phone, job_title, password):
    query = '''
                    CREATE (u:user {
                            email: $email
                            ,password: $password
                            }) with u
                    MATCH (p:person) WHERE p.email = $email
                    CREATE (u)-[:is]->(p)
                    '''
    with tms_db.session() as session:
            try:
                session.run(query, email=email, password=password, first_name=first_name, last_name=last_name, phone=phone, job_title=job_title)
                return True
            except Exception as e:
                msg = str(e)
                abort(500, msg)

def find_user(email):
    query = "MATCH (u:user) WHERE u.email = $email RETURN u"
    with tms_db.session() as session:
        try:
            result = session.run(query, email=email)
            record = result.single()
            if record:
                return True
            else:
                return None
        except Exception as e:
            msg = str(e)
            abort(500, msg)          

def register_user(first_name, last_name, email, phone, job_title, password):
    if find_user(email):
        return False
    else:
        return create_user(first_name, last_name, email, phone, job_title, password)


def find_person_by_email(email):
    query = "MATCH (p:person) where p.email = $email return p"
    with tms_db.session() as session:
        try:
            result = session.run(query, email=email)
            record = result.single()["p"]
            return record
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    
def find_person_by_tag(name,rel_type):
    query_start = "MATCH (t:tag)-[r1:"
    query_hyperedge = "includes]-(n)-[r2:"
    query_end = "]-(p:person) WHERE t.name = $name RETURN DISTINCT p ORDER BY p.last_name"

    if rel_type == "is_interested_in":
        query = query_start + rel_type + query_end
    elif rel_type == "works_on":
        query = query_start + query_hyperedge + rel_type + query_end
    elif rel_type == "has":
        query = query_start + query_hyperedge + rel_type + query_end

    with tms_db.session() as session:
        try:
            result = session.run(query, name=name,rel_type=rel_type)
            data = result.data()
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    
def get_tags():
    query = "MATCH (t:tag) RETURN t order by t.name"
    with tms_db.session() as session:
        try:
            result = session.run(query)
            if type(result) is type(None):
                return False
            data = result.data()
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    
def find_tag_by_name(name):
    query = "MATCH (t:tag) where t.name = $name RETURN t"
    with tms_db.session() as session:
        try:
            result = session.run(query,name=name)
            data = result.single()["t"]
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    
def find_task_by_tag(tag):
    query = "MATCH (t:task)-[r:includes]-(tag:tag) where tag.name = $tag RETURN t, elementid(t)"
    with tms_db.session() as session:
        try:
            result = session.run(query,tag=tag)
            data = result.data()
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)
      

def find_tags_by_email(email):
    query = "MATCH (p:person)-[r:is_interested_in]->(t:tag) where p.email = $email return t order by t.name"
    with tms_db.session() as session:
        try:
            result = session.run(query, email=email)
            data = result.data()
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)
        
def find_related_tags_by_name(name):
    query = "MATCH (t:tag)-[:related]-(t2:tag) where t2.name = $name return t"
    with tms_db.session() as session:
        try:
            result = session.run(query, name=name)
            data = result.data()
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)

def find_tags_by_search(search):
     query =  '''
            MATCH (t:tag)
            WHERE 0=1
            or apoc.text.fuzzyMatch(tolower(t.name), tolower($search))
            or tolower(t.name) contains tolower($search)
            RETURN t
            ORDER BY t.name
            '''
     with tms_db.session() as session:
        try:
            result = session.run(query, {"search": search})
            data = result.data()
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)
     
def find_persons_by_search(search):
     query =  '''
            MATCH (p:person)
            WHERE 0=1
            or apoc.text.fuzzyMatch(tolower(p.last_name), $search)
            or apoc.text.fuzzyMatch(tolower(p.first_name), $search)
            or tolower(p.last_name) contains $search
            or tolower(p.first_name) contains $search
            or tolower(p.job_title) contains $search
            RETURN p
            ORDER BY p.last_name
            '''
     with tms_db.session() as session:
        try:
            result = session.run(query, {"search": search})
            data = result.data()
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)
     

def find_tasks_by_email(email):
    query= "MATCH (p:person)-[r:works_on]->(t:task) where p.email = $email return t,elementid(t) order by t.start_date desc"
    with tms_db.session() as session:
        try:
            result = session.run(query, email=email)
            data = result.data()
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    
def find_tags_by_taskid(elementid):
    query = "MATCH (t:task)-[r2:includes]->(tag:tag) where elementid(t) = $elementid return tag order by tag.name"
    with tms_db.session() as session:
        try:
            result = session.run(query, elementid=elementid)
            data = result.data()
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg) 
    
def find_connected_tags_by_name(name, rel_type):
    if rel_type == "is_interested_in":
        query = "match (t:tag)-[r]-(p:person)-[r2]-(t2:tag) where t.name = $name"
    elif rel_type == "skilled":
        query = "match (t:tag)-[:includes]-(:skill)-[:has]-(p:person)-[:has]-(:skill)-[:includes]-(t2:tag) where t.name = $name"
    elif rel_type == "helped":
        query = "match (t:tag)-[:includes]-(:transfer)<-[:from]-(:person)-[:from]->(:transfer)-[:includes]-(t2:tag) where t.name = $name"
    elif rel_type == "worked":
        query = "match (t:tag)-[:includes]-(:task)<-[:works_on]-(:person)-[:works_on]->(:task)-[:includes]-(t2:tag) where t.name = $name"

    
    query += " return distinct t2.name as name order by t2.name LIMIT 4" # TODO: Limit entfernen

    with tms_db.session() as session:
        try:
            result = session.run(query, name=name)
            data = result.data()
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    
def find_task_by_taskid(elementid):
    query = "MATCH (t:task) where elementid(t) = $elementid return t"
    with tms_db.session() as session:
        try:
            result = session.run(query, elementid=elementid)
            data = result.single()["t"]
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    
def find_skills_by_email(email):
    query = "MATCH (p:person)-[r:has]->(s:skill)-[r2:includes]->(t:tag) where p.email = $email return s,t,elementid(s) order by t.name"
    with tms_db.session() as session:
        try:
            result = session.run(query, email=email)
            data = result.data()
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    
def find_person_with_shared_skills_by_email(tag,email):
    query = "MATCH (p1:person)-[rps1:has]->(s1:skill)-[rst1:includes]->(t:tag)<-[rst2:includes]-(s2:skill)<-[rps2:has]-(p2:person) where p1.email = $email and t.name = $tag return p2 order by p2.last_name"
    with tms_db.session() as session:
        try:
            result = session.run(query, email=email, tag=tag)
            data = result.data()
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    
def find_persons_by_taskid(elementid):
    query = "MATCH (t:task)<-[r:works_on]-(p:person) where elementid(t) = $elementid return p order by p.last_name"
    with tms_db.session() as session:
        try:
            result = session.run(query, elementid=elementid)
            data = result.data()
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    
def find_persons_by_input(input):
    query = '''
            MATCH (p:person)
            WITH p, apoc.text.join([p.first_name, p.last_name, p.job_title], " ") AS text
            WHERE tolower(text) contains tolower($input)
            RETURN p
            '''
    with tms_db.session() as session:
        try:
            result = session.run(query, input=input)
            data = result.data()
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    
def find_person_who_endorsed_by_skill(elementid):
    query = '''
    match (s:skill)<-[r:endorses]-(p:person)
    where elementid(s) = $elementid
    return distinct p
    order by p.last_name
    '''
    with tms_db.session() as tx:
        try:
            result = tx.run(query, elementid=elementid)
            data = result.data()
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)  

def get_count_endorsements_by_skill(elementid):
    query = '''
        match (s:skill)<-[r:endorses]-(:person)
        where elementid(s) = $elementid
        return count(r) as count
    '''
    with tms_db.session() as tx:
        try:
            result = tx.run(query, elementid=elementid)
            data = result.single()["count"]
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    
def get_endorsements_by_skill(elementid):
    query = '''
        match (s:skill)<-[r:endorses]-(p:person)
        where elementid(s) = $elementid
        return count(r) as count, distinct p
    '''
    with tms_db.session() as tx:
        try:
            result = tx.run(query, elementid=elementid)
            data = result.single()["count"]
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    
def get_recently_added_tags():
    query = "match (t:tag) where date(t.created) > date() - duration({days: 7})return t order by t.created desc"
    with tms_db.session() as tx:
        try:
            result = tx.run(query)
            data = result.data()
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    

def get_transfer():
    query = "match (p2:person)<-[r2:to]-(tx:transfer)<-[r:from]-(p1:person), (tx)-[r3:includes]->(t:tag) return tostring(tx.date) as date, p1 as p_from, p2 as p_to, t order by tx.date desc LIMIT 15"
    with tms_db.session() as tx:
        try:
            result = tx.run(query)
            data = [record for record in result]
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    
def get_transfer_tag_count(limit):
    query = "match (:transfer)-[r3:includes]->(t:tag) return count(t) as anz, t order by count(t) desc LIMIT $limit"  
    with tms_db.session() as tx:
        try:
            result = tx.run(query, limit=limit)
            data = [record for record in result]
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)

def get_top_transferor(limit):
    query = "match (:transfer)<-[r:from]-(p:person) return count(r) as anz, p order by count(r) desc LIMIT $limit"  
    with tms_db.session() as tx:
        try:
            result = tx.run(query, limit=limit)
            data = [record for record in result]
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)

def get_ongoing_task():
    query = "match (t:task) where t.end_date is null or t.end_date > date() return t,elementid(t) order by t.start_date desc"  
    with tms_db.session() as session:
        try:
            result = session.run(query)
            data = result.data()
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)

def get_top_skilled(limit):
    query = "match (:person)-[r:endorses]->(:skill)<-[:has]-(p:person) return count(r) as anz, p order by count(r) desc LIMIT $limit"  
    with tms_db.session() as tx:
        try:
            result = tx.run(query, limit=limit)
            data = [record for record in result]
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)

def get_top_working(limit):
    query = "match (p:person)-[r:works_on]->(:task) return count(r) as anz, p order by count(r) desc LIMIT $limit"  
    with tms_db.session() as tx:
        try:
            result = tx.run(query, limit=limit)
            data = [record for record in result]
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)

def get_persons():
    with tms_db.session() as session:
        try:
            result = session.run("MATCH (p:person) return p, elementid(p) as elementid order by p.last_name")
            data = result.data()
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    

def find_transfer_by_email(email):
    query = "match (p2:person)<-[:to]-(tx:transfer)<-[:from]-(p1:person), (tx)-[:includes]->(t:tag) where p2.email = $email or p1.email = $email return tx.date as date, p1 as p_from, p2 as p_to, t order by tx.date desc"
    with tms_db.session() as tx:
        try:
            result = tx.run(query, email=email)
            data = [record for record in result]
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    
def get_transferorCount_by_tag(tag):
    query = "match (t:tag)<-[r3:includes]-(tx:transfer)<-[r:from]-(p1:person) where t.name = $tag return count(tx) as anz, p1 as p_from order by count(tx) desc, p1.last_name "
    with tms_db.session() as tx:
        try:
            result = tx.run(query, tag=tag)
            data = [record for record in result]
            return data    
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    
def find_transfer_by_tag(tag):
    query = "match (t:tag)<-[r3:includes]-(tx:transfer)<-[r:from]-(p1:person) where t.name = $tag return count(p1) as anz, tx.date as date, p1 as p_from, t order by count(p1) desc, p1.last_name asc"
    with tms_db.session() as tx:
        try:
            result = tx.run(query, tag=tag)
            data = [record for record in result]
            return data    
        except Exception as e:
            msg = str(e)
            abort(500, msg)
        
# TODO: return auserhalb session?
    
def get_popular_tags(rel_type):
    if rel_type == "is_interested_in":
            query = "MATCH (t:tag)-[r:" + rel_type + "]-(m) RETURN t.name as name, count(r) as anz ORDER BY count(r) DESC,t.name asc LIMIT 5"
    else:
        query = "MATCH (t:tag)-[r:includes]-(m) where (m)-[:" + rel_type + "]-() RETURN t.name as name, count(r) as anz ORDER BY count(r) DESC,t.name asc LIMIT 5"

    with tms_db.session() as tx:
        try:
            result = tx.run(query)
            data = result.data()
            return data
        except Exception as e:
            msg = str(e)
            abort(500, msg)

def get_similar_tags():
    query = '''
    MATCH (t:tag), (t2:tag)
            WHERE (apoc.text.fuzzyMatch(t.name, t2.name) or t.name contains t2.name)
            and elementid(t) <> elementid(t2)
            and not ((t)-[:related]-(t2))
            RETURN t, t2
            ORDER BY t.name
    '''
    with tms_db.session() as tx:
        try:
            result = tx.run(query)
            data = result.data()
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    return data

def relate_tags(tag1,tag2):
    query = '''
    MATCH (t:tag), (t2:tag)
    WHERE t.name = $tag1 and t2.name = $tag2
    CREATE (t)-[r:related]->(t2)
    '''
    with tms_db.session() as tx:
        try:
            result = tx.run(query, tag1=tag1, tag2=tag2)
            data = result.data()
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    return data

def merge_tags(tag1,tag2):
    query = '''
    MATCH (t:tag), (t2:tag)
    WHERE t.name = $tag1 and t2.name = $tag2
    CALL apoc.refactor.mergeNodes([t, t2], {properties: 'overwrite'})
    YIELD node
    RETURN node
    '''
    with tms_db.session() as tx:
        try:
            result = tx.run(query, tag1=tag1, tag2=tag2)
            data = result.data()
        except Exception as e:
            msg = str(e)
            abort(500, msg)
    return data

def create_tag(name):
    if find_tag(name):
        return False
    else:
        query = '''
                CREATE (t:tag {
                        name: $name
                        ,created: datetime()
                        ,last_modified: datetime()
                        })
                '''
        with tms_db.session() as session:

            try:
                session.run(query, name=name)
                return True
            except Exception as e:
                msg = str(e)
                abort(500, msg)
        
def find_tag(name):
    query = "MATCH (t:tag) WHERE t.name = $name RETURN t"
    with tms_db.session() as session:
        try:
            result = session.run(query, name=name)
            record = result.single()
            if record:
                return True
            else:
                return None
        except Exception as e:
            msg = str(e)
            abort(500, msg)

def add_tag_by_reltype(tag, email, rel_type):
    query = '''merge (t:tag {{name: $tag}})
                                    ON CREATE SET t.created = datetime(), t.last_modified = datetime()
                                    with t
                                    match (p:person) where p.email = $email
                                    merge (p)-[r:{}]->(t)
                                    ON CREATE SET r.created = datetime()
                                    '''.format(rel_type)
    with tms_db.session() as tx:
        try:
            tx.run(query, tag=tag, email=email)
        except:
            return abort(500)
        
def create_transfer(p_from,p_to,tag,date):
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
    with tms_db.session() as tx:
        try:
            tx.run(query, p_from=p_from, p_to=p_to, tag=tag, date=date)
        except:
            return abort(500)
        
def create_endorsement(elementid,email):
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
            return abort(500)
        
def create_task(desc, title, start_date, end_date, email, tags, collaborators):

    query = '''
        CREATE (t:task {created: datetime(), last_modified: datetime(), description: $desc, title: $title, start_date: $start_date, end_date: $end_date}) WITH t
        MATCH (p:person) WHERE p.email = $email
        CREATE (p)-[:works_on]->(t)
        RETURN elementid(t) AS elementid
    '''
    query2 = '''
        MATCH (t:task), (p:person) WHERE elementid(t) = $elementid and p.email = $collaborator
        CREATE (p)-[:works_on]->(t) 
    '''
    query3 = '''
        MERGE (tag:tag {name: $tag})
        ON CREATE SET tag.created = datetime(), tag.last_modified = datetime()
        with tag
        MATCH (t:task) WHERE elementid(t) = $elementid
        CREATE (t)-[:includes]->(tag)
    '''
    with tms_db.session() as tx:
        try:
            result = tx.run(query, desc=desc, title=title, start_date=start_date, end_date=end_date, email=email)
            elementid = result.single()["elementid"]
        except:
            return abort(500) 
        
        for collaborator in  collaborators:
            try:
                tx.run(query2, collaborator=collaborator, elementid=elementid)
            except:
                return abort(500) 
        for tag in tags:
            try:
                tx.run(query3, tag=tag, elementid=elementid)
            except:
                return abort(500)

def create_skill(tag,desc,email):
    query = '''
        MERGE (t:tag {name: $tag})
        ON CREATE SET t.created = datetime(), t.last_modified = datetime()
        CREATE (s:skill {description: $desc, created: datetime(), last_modified: datetime()})
        with s,t
        MATCH (p:person) WHERE p.email = $email
        MERGE (p)-[:has]->(s)-[:includes]->(t)
    '''
    with tms_db.session() as tx:
        try:
            tx.run(query, tag=tag, desc=desc, email=email)
        except:
            return abort(500)

def remove_skill_by_tag(tag,email):
    query = "match (t:tag)<-[r1:includes]-(s:skill)<-[r2:has]-(p:person) where t.name = $tag and p.email = $email delete r1,s,r2"

    with tms_db.session() as tx:
        try:
            tx.run(query, tag=tag, email=email)
        except:
            return abort(500)
        
def remove_interest(tag,email,checked_values):
    query = "match (t:tag)<-[r:is_interested_in]-(p:person) where t.name = $tag and p.email = $email delete r"

    with tms_db.session() as tx:
        for tag in checked_values:
                    try:        
                        tx.run(query, tag=tag, email=email)
                    except:
                        return abort(500)

def check_login(email,password):
    query = "MATCH (u:user) where u.email = $email return u.password, u.is_admin"

    with tms_db.session() as tx:
        try:        
            result = tx.run(query, password=password, email=email)
            record = result.single()
            return record
        except:
            return abort(500)

