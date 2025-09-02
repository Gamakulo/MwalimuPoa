# AI Study Buddy — Flashcard Generator (Flask + MySQL + HF)

A tiny end-to-end app for beginners: paste notes → get AI-generated Q/A → flip cards → save to MySQL.

## Quickstart

### 1) Clone and install
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows: .venv\Scripts\activate
pip install -r requirements.txt 
## when presented with an Error install packages directly (skip the file)
python -m pip install Flask==3.0.3 Flask-CORS==4.0.1 SQLAlchemy==2.0.32 PyMySQL==1.1.1 python-dotenv==1.0.1 requests==2.32.3
```

### 2) Configure database
Create a MySQL database and user, then set `DATABASE_URL` in `.env` like:
```
DATABASE_URL=mysql+pymysql://USER:YOUR_PASSWORD@localhost:3306/study_buddy
```
Or for a quick local try, omit `.env` and SQLite fallback `study_buddy.db` will be created.

Optionally run `schema.sql` to pre-create the tables (SQLAlchemy also auto-creates).

### 3) Hugging Face Inference API (optional but better)
- Get a token: https://huggingface.co/settings/tokens
- Add to `.env`:
```
HF_API_TOKEN=hf_xxx
HF_QG_MODEL=iarfmoose/t5-base-question-generator
```
If unset, the app uses a simple local fallback to produce questions.

### 4) Run
```bash
flask --app app run --debug
```
Open http://localhost:5000

## Architecture

- **Frontend**: Simple HTML/CSS cards with a flip animation and tiny JS for state.
- **Backend**: Flask REST endpoints:
  - `POST /api/generate` → calls Hugging Face to build Q/A (or local fallback)
  - `POST /api/save` → writes a set + its cards to MySQL
  - `GET /api/sets` and `GET /api/sets/:id` → browse saved sets
- **DB**: MySQL via SQLAlchemy models (`FlashcardSet`, `Flashcard`)

## Notes & Tips

- For models that don't return `Q:`/`A:` lines, the backend tries to parse sensibly, else falls back.
- Keep tokens on the server; never expose your HF token to the browser.
- CORS is enabled if you want to host the frontend separately.
- Production hardening: add user auth, rate limits, validation, migrations, and CSRF protection.
