import os, sqlite3, time
from datetime import datetime, timezone
from urllib.parse import urlparse
import requests
from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
DB_PATH = os.environ.get("DATABASE_PATH", "api_guardian.db")

def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS endpoints (id INTEGER PRIMARY KEY, name TEXT NOT NULL, url TEXT UNIQUE NOT NULL)")
        c.execute("""CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY, endpoint_id INTEGER NOT NULL, status TEXT NOT NULL,
            status_code INTEGER, response_ms INTEGER, checked_at TEXT, message TEXT,
            FOREIGN KEY(endpoint_id) REFERENCES endpoints(id))""")

def valid_url(value):
    p = urlparse(value)
    return p.scheme in ("http", "https") and bool(p.netloc)

def check_url(url):
    start = time.perf_counter()
    try:
        r = requests.get(url, timeout=8)
        ms = round((time.perf_counter()-start)*1000)
        ok = 200 <= r.status_code < 400
        return {"status":"UP" if ok else "DOWN", "code":r.status_code, "ms":ms,
                "message":"Endpoint responded." if ok else f"HTTP {r.status_code}"}
    except requests.RequestException as e:
        return {"status":"DOWN", "code":None,
                "ms":round((time.perf_counter()-start)*1000), "message":str(e)[:160]}

def record(endpoint_id, result):
    with db() as c:
        c.execute("INSERT INTO checks(endpoint_id,status,status_code,response_ms,checked_at,message) VALUES(?,?,?,?,?,?)",
                  (endpoint_id,result["status"],result["code"],result["ms"],
                   datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),result["message"]))

@app.route("/")
def index():
    with db() as c:
        endpoints = c.execute("""SELECT e.*,
          (SELECT status FROM checks WHERE endpoint_id=e.id ORDER BY id DESC LIMIT 1) latest_status,
          (SELECT status_code FROM checks WHERE endpoint_id=e.id ORDER BY id DESC LIMIT 1) latest_code,
          (SELECT response_ms FROM checks WHERE endpoint_id=e.id ORDER BY id DESC LIMIT 1) latest_ms
          FROM endpoints e ORDER BY e.id DESC""").fetchall()
        history = c.execute("""SELECT checks.*, endpoints.name FROM checks
          JOIN endpoints ON endpoints.id=checks.endpoint_id ORDER BY checks.id DESC LIMIT 8""").fetchall()
    return render_template("index.html", endpoints=endpoints, history=history,
        total=len(endpoints), up=sum(x["latest_status"]=="UP" for x in endpoints),
        down=sum(x["latest_status"]=="DOWN" for x in endpoints))

@app.post("/endpoints")
def add_endpoint():
    name, url = request.form.get("name","").strip(), request.form.get("url","").strip()
    if not name or not valid_url(url):
        flash("Enter a name and a valid HTTP or HTTPS URL.", "error")
    else:
        try:
            with db() as c: c.execute("INSERT INTO endpoints(name,url) VALUES(?,?)",(name,url))
            flash("Endpoint added.", "success")
        except sqlite3.IntegrityError: flash("That URL is already registered.", "error")
    return redirect(url_for("index"))

@app.post("/check/<int:endpoint_id>")
def check_one(endpoint_id):
    with db() as c: item=c.execute("SELECT * FROM endpoints WHERE id=?",(endpoint_id,)).fetchone()
    if item is None: flash("Endpoint not found.", "error")
    else:
        result=check_url(item["url"]); record(endpoint_id,result)
        flash(f'{item["name"]}: {result["status"]} — {result["message"]}', "success" if result["status"]=="UP" else "error")
    return redirect(url_for("index"))

@app.post("/check-all")
def check_all():
    with db() as c: items=c.execute("SELECT * FROM endpoints").fetchall()
    for item in items: record(item["id"],check_url(item["url"]))
    flash(f"Checked {len(items)} endpoint(s).", "success")
    return redirect(url_for("index"))

@app.post("/delete/<int:endpoint_id>")
def delete_endpoint(endpoint_id):
    with db() as c:
        c.execute("DELETE FROM checks WHERE endpoint_id=?",(endpoint_id,))
        c.execute("DELETE FROM endpoints WHERE id=?",(endpoint_id,))
    flash("Endpoint deleted.", "success")
    return redirect(url_for("index"))

@app.get("/health")
def health():
    return {"status":"healthy","application":"API Guardian"},200

init_db()
if __name__ == "__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
