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
    
def find_all_tags():
    with tms_db.session() as session:
        result = session.run("MATCH (t:tag) RETURN t")
        data = result.data()
        return data
      

def find_tags_by_email(email):
    with tms_db.session() as session:
        result = session.run("MATCH (p:person)-[r:follows]->(t:tag) where p.email = $email return t", email=email)
        data = result.data()
        return data

def find_tasks_by_email(email):
    with tms_db.session() as session:
        result = session.run("MATCH (p:person)-[r:works_on]->(t:task) where p.email = $email return t,elementid(t)", email=email)
        data = result.data()
        return data
    
def find_tags_by_taskid(elementid):
    with tms_db.session() as session:
        result = session.run("MATCH (t:task)-[r2:includes]->(tag:tag) where elementid(t) = $elementid return tag", elementid=elementid)
        data = result.data()
        return data
    
def find_skills_by_email(email):
    with tms_db.session() as session:
        result = session.run("MATCH (p:person)-[r:has]->(s:skill)-[r2:includes]->(t:tag) where p.email = $email return s,t,elementid(s)", email=email)
        data = result.data()
        return data
    
def find_person_with_shared_skills_by_email(tag,email):
    with tms_db.session() as session:
        result = session.run("MATCH (p1:person)-[rps1:has]->(s1:skill)-[rst1:includes]->(t:tag)<-[rst2:includes]-(s2:skill)<-[rps2:has]-(p2:person) where p1.email = $email and t.name = $tag return p2", email=email, tag=tag)
        data = result.data()
        return data
    
def find_persons_by_taskid(elementid):
    with tms_db.session() as session:
        result = session.run("MATCH (t:task)<-[r:works_on]-(p:person) where elementid(t) = $elementid return p", elementid=elementid)
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
    query = "match (t:tag) return t order by t.created desc limit 10"
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

def get_persons():
    with tms_db.session() as session:
        result = session.run("MATCH (p:person) return p.first_name as first_name, p.last_name as last_name, elementid(p) as elementid, p.email as email")
        data = result.data()
        return data
    
def find_transaction_by_email(email):
    query = "match (p2:person)<-[r2:to]-(tx:transaction)<-[r:from]-(p1:person), (tx)-[r3:includes]->(t:tag) where p2.email = $email1 or p1.email = $email2 return tx.date as date, p1 as p_from, p2 as p_to, t order by tx.date desc"
    with tms_db.session() as tx:
        result = tx.run(query, email1=email, email2=email)
        data = [record for record in result]
        return data
    
def get_popular_tags(rel_type):
    if rel_type == "follows":
            query = "MATCH (t:tag)-[r:" + rel_type + "]-(m) RETURN t.name as name, count(r) as count ORDER BY count(r) DESC LIMIT 10"
    else:
        query = "MATCH (t:tag)-[r:includes]-(m) where (m)-[:" + rel_type + "]-() RETURN t.name as name, count(r) as count ORDER BY count(r) DESC LIMIT 10"

    with tms_db.session() as tx:
        result = tx.run(query)
        data = result.data()
        return data

def get_unpopular_tags(rel_type):
    if rel_type == "follows":
            query = "MATCH (t:tag)-[r:" + rel_type + "]-(m) RETURN t.name as name, count(r) as count ORDER BY count(r) ASC LIMIT 10"
    else:
        query = "MATCH (t:tag)-[r:includes]-(m) where (m)-[:" + rel_type + "]-() RETURN t.name as name, count(r) as count ORDER BY count(r) ASC LIMIT 10"

    with tms_db.session() as tx:
        result = tx.run(query)
        data = result.data()
        return data

def merge():
    query = "match (t:tag) return t.name"

    with tms_db.session() as session:
        result = session.run(query)
        data = result.data()
        return data
