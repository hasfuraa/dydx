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

## Repository
https://github.com/hasfuraa/dydx
