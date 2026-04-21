# HabitBloom

HabitBloom is a 21-day habit tracking website with:

- signup and login
- secure password hashing
- cookie-based sessions
- persistent habit progress storage
- a Python standard-library backend
- SQLite with deploy-friendly persistent storage support

## Project Structure

- `server.py` - backend server and API
- `index.html` - main tracker page
- `login.html` - login page
- `signup.html` - signup page
- `styles.css` - shared styling
- `auth.js` - auth-related frontend logic
- `script.js` - tracker frontend logic
- `data/` - local SQLite storage folder
- `railway.json` - Railway startup config
- `render.yaml` - Render service config
- `Procfile` - generic process startup file
- `.env.example` - example environment variables
- `DEPLOY.md` - deployment instructions

## Run Locally

Use the bundled runtime already configured in this workspace or run:

```powershell
python server.py
```

Then open:

`http://127.0.0.1:8000/`

## Deploy Quickly

The easiest path for this version is Railway with a persistent volume.

1. Push this folder to GitHub.
2. Create a Railway project from the repo.
3. Attach a volume mounted at `/app/data`.
4. Set environment variables:
   - `DATA_DIR=/app/data`
   - `COOKIE_SECURE=true`
5. Deploy.

## Notes

- This app uses SQLite, so a persistent disk/volume is required for public hosting.
- If you want to scale to many concurrent users later, move the app to PostgreSQL.
