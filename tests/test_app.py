import os, tempfile
import pytest
import app

@pytest.fixture
def client(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(app, "DB_PATH", path)
    app.init_db()
    app.app.config.update(TESTING=True)
    with app.app.test_client() as c: yield c
    os.remove(path)

def test_home(client):
    r=client.get("/")
    assert r.status_code==200 and b"API Guardian" in r.data

def test_health(client):
    r=client.get("/health")
    assert r.status_code==200 and r.get_json()["status"]=="healthy"

def test_add_endpoint(client):
    r=client.post("/endpoints",data={"name":"Demo API","url":"https://example.com"},follow_redirects=True)
    assert r.status_code==200 and b"Demo API" in r.data

def test_reject_bad_url(client):
    r=client.post("/endpoints",data={"name":"Bad","url":"not-a-url"},follow_redirects=True)
    assert b"valid HTTP" in r.data

def test_check_success(monkeypatch):
    class Response: status_code=200
    monkeypatch.setattr(app.requests,"get",lambda *a,**k:Response())
    assert app.check_url("https://example.com")["status"]=="UP"

def test_check_timeout(monkeypatch):
    def timeout(*a,**k): raise app.requests.Timeout("timeout")
    monkeypatch.setattr(app.requests,"get",timeout)
    assert app.check_url("https://example.com")["status"]=="DOWN"
