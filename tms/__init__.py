from .views import app
from .models import tms_db

with tms_db.session() as session:
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:person) REQUIRE p.email IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:person) REQUIRE p.phone IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (t:tag) REQUIRE t.name IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (u:user) REQUIRE u.email IS UNIQUE")

