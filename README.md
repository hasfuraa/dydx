# dydx — Math Grading MVP

A lightweight web app for professors to create classes/problem sets, accept student submissions, and auto‑grade using an LLM with rubric‑based scoring.

## Features
- Professor workflow: create classes → problem sets → problems (PDF prompts) → auto‑generated rubrics → review submissions
- Student workflow: sign up → upload draft → finalize → view rubric + feedback → regrade → appeal
- Auto‑grading with OpenAI vision models (configurable)
- Role‑based dashboards

## Quick Start (Local)
```bash
# Create and activate venv
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create admin (professor) account
python manage.py createsuperuser

# Optional: set OpenAI API key and model
export OPENAI_API_KEY="your-key"
export OPENAI_MODEL="gpt-4.1-2025-04-14"

# Start server
python manage.py runserver
```

Then visit:
- `http://127.0.0.1:8000/login/` for login
- `http://127.0.0.1:8000/signup/` for student signup

## Notes
- To make a user a professor, mark them as `staff` in Django admin (`/admin/`).
- Rubrics are generated from the problem PDF; if the API key is missing, rubric generation will error.
- Final grades reflect the best AI regrade score.

## Render Deployment (WIP)
This repo includes `render.yaml` and `build.sh` for a simple Render deploy.

High-level steps:
1. Push to GitHub.
2. Create a new Render project and connect the repo.
3. Render will provision Postgres and deploy the web service.
4. Add your domain and update DNS to point at Render.

### First admin user (Render free tier)
Render free tier doesn’t include a shell. We bootstrap an admin user at deploy time:

- Set env vars in Render:
  - `ADMIN_EMAIL`
  - `ADMIN_PASSWORD`
  - (optional) `ADMIN_USERNAME`
- On deploy, `python manage.py bootstrap_admin` creates the first admin.
- After that, you can remove those env vars if desired.

### Persistent media (Render disk)
For the MVP, we use a Render persistent disk mounted at `/var/data` and set:
- `MEDIA_ROOT=/var/data/media`

This keeps uploads across deploys on the same service instance.

## Repository
https://github.com/hasfuraa/dydx
