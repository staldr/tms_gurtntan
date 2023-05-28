# Voraussetzungen
* Docker Desktop Installation
* Internetverbindung
## Applikation starten
öffnen Sie die Kommandozeile im Rootverzeichnis und führen Sie folgende Befehle aus:
```sh
docker-compose up -d
```
Die Applikation steht unter `http://localhost:5000` zur Verfügung.
## Applikation stoppen
öffnen Sie die Kommandozeile im Rootverzeichnis und führen Sie folgende Befehle aus:
```sh
docker-compose stop  
```
## Datenbankzugriff
Die Credentials um direkt auf die Datenbankinstanz (z.B. via Neo4j Browser) zuzugreifen, befinden sich im File `tms\credentials-ff8b3a26.env`

## Anmeldeinformationen Administrator
E-Mail: admin@tms.ch
Passwort: admin

Alternativ kann an jeden beliebigen User mit folgendem Cypher-Statement Admin-Rechte erteilt werden:
```cypher
MATCH (u:user) WHERE u.email = $email set u.is_admin = True RETURN u
```

