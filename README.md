# API Guardian

A web application for registering public HTTP/HTTPS API endpoints, manually checking availability, measuring response time, and reviewing recent check history.

## DevOps implementation
- Git and GitHub: source control and collaboration.
- GitHub Actions: Continuous Integration runs Pytest on pushes and pull requests to `main`.
- Render: Continuous Deployment can deploy the latest commit when the service is linked to this repository and Auto-Deploy is enabled.
- `/health`: health-check endpoint for the hosting platform.

## Run locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -v
python app.py
```
Open http://127.0.0.1:5000.

## Scope and limitations
Checks are user-triggered, not scheduled background monitoring. The app does not send email/SMS alerts and has no user accounts; visitors share the same dashboard and database. SQLite on some free hosting instances may be ephemeral across restarts/redeployments. This is an academic prototype, not a production security scanner. Only check public endpoints you own or are authorized to test. Production improvements include authentication, per-user data separation, request rate limits, URL/IP restrictions, durable storage, scheduled checks and alerting.
Automatic deployment verification test.