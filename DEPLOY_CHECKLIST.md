# Deploy Checklist

## Before Deploying

- Keep `server.py` in the repo root.
- Keep `railway.json`, `Procfile`, and `render.yaml` in the repo root.
- Do not upload the local SQLite database file if it contains test data.
- Make sure `data/` exists in the project.

## Railway

- Push repo to GitHub
- Create Railway project from GitHub repo
- Add volume mounted to `/app/data`
- Set `DATA_DIR=/app/data`
- Set `COOKIE_SECURE=true`
- Deploy

## Render

- Push repo to GitHub
- Create Web Service from repo
- Add persistent disk
- Set `DATA_DIR` to mounted disk path
- Set `COOKIE_SECURE=true`
- Start command: `python server.py $PORT`

## Check After Deploy

- Open `/health`
- Open `/signup.html`
- Create an account
- Log in
- Create a habit
- Refresh and confirm the habit data still exists
