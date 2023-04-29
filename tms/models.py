# Classes and functions
from flask import abort, jsonify, make_response
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="tms/credentials-ff8b3a26.env")

url = os.environ.get('NEO4J_URI')
username = os.environ.get('NEO4J_USERNAME')
password = os.environ.get('NEO4J_PASSWORD')

tms_db = GraphDatabase.driver(url, auth=(username, password))

class Person:
    def __init__(self, first_name, last_name, email, phone, job_title):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.phone = phone
        self.job_title = job_title

#################################
    @classmethod
    def find_by_email(cls, email):
        with tms_db.session() as session:
            result = session.run("MATCH (p:person) WHERE p.email = $email RETURN p", email=email)
            record = result.single()
            if record:
                person = record['p']
                return cls(person['first_name'], person['last_name'], person['email'],  person['phone'],  person['job_title'])
            else:
                return None

#################################
    @classmethod
    def create_person(cls, person):
        if cls.find_by_email(person.email):
            return False
        else:
            with tms_db.session() as session:
                query = '''
                        CREATE (p:person {
                                first_name: $first_name
                                ,last_name: $last_name
                                ,email: $email
                                ,phone: $phone
                                ,job_title: $job_title
                                })
                        RETURN p
                        '''
                result = session.run(query, first_name=person.first_name, last_name=person.last_name, email=person.email, phone=person.phone, job_title=person.job_title)
                return result
        
class User(Person):
    def __init__(self, first_name, last_name, email, phone, job_title, password):
        super().__init__(first_name, last_name, email, phone, job_title)
        self.password = password

    @classmethod
    def find(cls, email):
        with tms_db.session() as session:
            result = session.run("MATCH (u:user) WHERE u.email = $email RETURN u", email=email)
            record = result.single()
            if record:
                return True
            else:
                return None
            
    @classmethod
    def create_user(cls, user):
        with tms_db.session() as session:
                query = '''
                        MERGE (u:user {
                                email: $email
                                ,password: $password
                                })
                        MERGE (p:person {
                                email: $email
                                })
                        CREATE (u)-[r:is]->(p)
                        RETURN u,r,p
                        '''
                session.run(query, email=user.email, password=user.password)


    @classmethod
    def register(cls, user):
        if cls.find(user.email):
            return False
        else:
            super().create_person(user)
            cls.create_user(user)
            return True


def find_person_by_email(email):
    with tms_db.session() as session:
        try:
            result = session.run("MATCH (p:person) where p.email = $email return p", email=email)
            record = result.single()["p"]
        except TypeError as e:
            data = {'message': 'This is an example response.'}
            response = make_response(jsonify(data))
            response.status = '200 OK'
            return response
        return record
    
def find_person_by_tag(name,rel_type):
    query_start = "MATCH (t:tag)-[r1:"
    query_hyperedge = "includes]-(n)-[r2:"
    query_end = "]-(p:person) WHERE t.name = $name RETURN DISTINCT p ORDER BY p.last_name"
    if rel_type == "follows":
        query = query_start + rel_type + query_end
    elif rel_type == "works_on":
        query = query_start + query_hyperedge + rel_type + query_end
    elif rel_type == "has":
        query = query_start + query_hyperedge + rel_type + query_end

    with tms_db.session() as session:
        result = session.run(query, name=name,rel_type=rel_type)
        data = result.data()
        return data
    
def get_tags():
    with tms_db.session() as session:
        result = session.run("MATCH (t:tag) RETURN t order by t.name")
        data = result.data()
        return data
    
def find_tag_by_name(name):
    query = "MATCH (t:tag) where t.name = $name RETURN t"
    with tms_db.session() as session:
        result = session.run(query,name=name)
        data = result.single()["t"]
        return data
    
def find_task_by_tag(tag):
    query = "MATCH (t:task)-[r:includes]-(tag:tag) where tag.name = $tag RETURN t, elementid(t)"
    with tms_db.session() as session:
        result = session.run(query,tag=tag)
        data = result.data()
        return data
      

def find_tags_by_email(email):
    with tms_db.session() as session:
        result = session.run("MATCH (p:person)-[r:follows]->(t:tag) where p.email = $email return t order by t.name", email=email)
        data = result.data()
        return data

def find_tasks_by_email(email):
    with tms_db.session() as session:
        result = session.run("MATCH (p:person)-[r:works_on]->(t:task) where p.email = $email return t,elementid(t) order by t.start_date desc", email=email)
        data = result.data()
        return data
    
def find_tags_by_taskid(elementid):
    with tms_db.session() as session:
        result = session.run("MATCH (t:task)-[r2:includes]->(tag:tag) where elementid(t) = $elementid return tag order by tag.name", elementid=elementid)
        data = result.data()
        return data
    
    
def find_connected_tags_by_name(name, rel_type):
    if rel_type == "follows":
        query = "match (t:tag)-[r]-(p:person)-[r2]-(t2:tag) where t.name = $name"
    elif rel_type == "skilled":
        query = "match (t:tag)-[:includes]-(:skill)-[:has]-(p:person)-[:has]-(:skill)-[:includes]-(t2:tag) where t.name = $name"
    elif rel_type == "helped":
        query = "match (t:tag)-[:includes]-(:transaction)<-[:from]-(:person)-[:from]->(:transaction)-[:includes]-(t2:tag) where t.name = $name"
    elif rel_type == "worked":
        query = "match (t:tag)-[:includes]-(:task)<-[:works_on]-(:person)-[:works_on]->(:task)-[:includes]-(t2:tag) where t.name = $name"

    
    query += " return distinct t2.name as name order by t2.name"

    with tms_db.session() as session:
        result = session.run(query, name=name)
        data = result.data()
        return data
    
def find_task_by_taskid(elementid):
    with tms_db.session() as session:
        result = session.run("MATCH (t:task) where elementid(t) = $elementid return t", elementid=elementid)
        data = result.single()["t"]
        return data
    
def find_skills_by_email(email):
    with tms_db.session() as session:
        result = session.run("MATCH (p:person)-[r:has]->(s:skill)-[r2:includes]->(t:tag) where p.email = $email return s,t,elementid(s) order by t.name", email=email)
        data = result.data()
        return data
    
def find_person_with_shared_skills_by_email(tag,email):
    with tms_db.session() as session:
        result = session.run("MATCH (p1:person)-[rps1:has]->(s1:skill)-[rst1:includes]->(t:tag)<-[rst2:includes]-(s2:skill)<-[rps2:has]-(p2:person) where p1.email = $email and t.name = $tag return p2 order by p2.last_name", email=email, tag=tag)
        data = result.data()
        return data
    
def find_persons_by_taskid(elementid):
    with tms_db.session() as session:
        result = session.run("MATCH (t:task)<-[r:works_on]-(p:person) where elementid(t) = $elementid return p order by p.last_name", elementid=elementid)
        data = result.data()
        return data
    
def find_persons_by_input(input):
    with tms_db.session() as session:
        result = session.run('''MATCH (p:person)
                                WITH p, apoc.text.join([p.first_name, p.last_name, p.job_title], " ") AS text
                                WHERE tolower(text) contains tolower($input)
                                RETURN p''', input=input)
        data = result.data()
        return data
    
def find_person_who_endorsed_by_skill(elementid):
    query = '''
    match (s:skill)<-[r:endorses]-(p:person)
    where elementid(s) = $elementid
    return distinct p
    order by p.last_name
    '''
    with tms_db.session() as tx:
        result = tx.run(query, elementid=elementid)
        data = result.data()
    return data
       

def get_count_endorsements_by_skill(elementid):
    query = '''
        match (s:skill)<-[r:endorses]-(p:person)
        where elementid(s) = $elementid
        return count(r) as count
    '''
    with tms_db.session() as tx:
        result = tx.run(query, elementid=elementid)
        data = result.single()["count"]
        return data
    
def get_recently_added_tags():
    query = "match (t:tag) where date(t.created) > date() - duration({days: 7})return t order by t.created desc"
    with tms_db.session() as tx:
        result = tx.run(query)
        data = result.data()
        return data

def get_transaction():
    query = "match (p2:person)<-[r2:to]-(tx:transaction)<-[r:from]-(p1:person), (tx)-[r3:includes]->(t:tag) return tostring(tx.date) as date, p1 as p_from, p2 as p_to, t order by tx.date desc"
    with tms_db.session() as tx:
        result = tx.run(query)
        data = [record for record in result]
        return data
    
def get_transaction_tag_count():
    query = "match (tx)-[r3:includes]->(t:tag) return count(t) as anz, t order by count(t) desc"  
    with tms_db.session() as tx:
        result = tx.run(query)
        data = [record for record in result]
        return data

def get_persons():
    with tms_db.session() as session:
        result = session.run("MATCH (p:person) return p.first_name as first_name, p.last_name as last_name, elementid(p) as elementid, p.email as email order by p.last_name")
        data = result.data()
        return data
    
def find_transaction_by_email(email):
    query = "match (p2:person)<-[r2:to]-(tx:transaction)<-[r:from]-(p1:person), (tx)-[r3:includes]->(t:tag) where p2.email = $email1 or p1.email = $email2 return tx.date as date, p1 as p_from, p2 as p_to, t order by tx.date desc"
    with tms_db.session() as tx:
        result = tx.run(query, email1=email, email2=email)
        data = [record for record in result]
        return data
    
def find_transaction_by_tag(tag):
    query = "match (t:tag)<-[r3:includes]-(tx:transaction)<-[r:from]-(p1:person) where t.name = $tag return count(p1) as anz, tx.date as date, p1 as p_from, t order by count(p1) desc, p1.last_name asc"
    #query = "match (p2:person)<-[r2:to]-(tx:transaction)<-[r:from]-(p1:person), (tx)-[r3:includes]->(t:tag) where t.name = $tag return count(distinct p1) as count, tx.date as date, p1 as p_from, p2 as p_to, t order by p1.last_name asc"
    with tms_db.session() as tx:
        result = tx.run(query, tag=tag)
        data = [record for record in result]
        return data    
    
def get_popular_tags(rel_type):
    if rel_type == "follows":
            query = "MATCH (t:tag)-[r:" + rel_type + "]-(m) RETURN t.name as name, count(r) as anz ORDER BY count(r) DESC,t.name asc"
    else:
        query = "MATCH (t:tag)-[r:includes]-(m) where (m)-[:" + rel_type + "]-() RETURN t.name as name, count(r) as anz ORDER BY count(r) DESC,t.name asc"

    with tms_db.session() as tx:
        result = tx.run(query)
        data = result.data()
        return data
'''
def get_unpopular_tags(rel_type):
    if rel_type == "follows":
            query = "MATCH (t:tag)-[r:" + rel_type + "]-(m) RETURN t.name as name, count(r) as count ORDER BY count(r) ASC"
    else:
        query = "MATCH (t:tag)-[r:includes]-(m) where (m)-[:" + rel_type + "]-() RETURN t.name as name, count(r) as count ORDER BY count(r) ASC"

    with tms_db.session() as tx:
        result = tx.run(query)
        data = result.data()
        return data
'''

# test similar tags
def merge():
    tags = get_tags()
    import spacy

    nlp = spacy.load("en_core_web_sm")

    terms = list()
    for tag in tags:
        terms.append(tag['t']['name'])

    terms_freq = dict()
    for term in terms:
        similarity_scores = []
        for other_term in terms:
            if term != other_term:
                print(term," <--> ", other_term)
                similarity = nlp(term).similarity(nlp(other_term))
                if similarity > 0.90:
                    similarity_scores.append((other_term, similarity))
                if similarity_scores:
                    similarity_scores.sort(key=lambda x: x[1], reverse=True)
                    terms_freq[term] = similarity_scores

    return str(terms_freq)

