# Deploy HabitBloom

This app currently uses SQLite, so public hosting should use persistent storage.

## Railway

1. Push this project to GitHub.
2. Create a new Railway project from the repo.
3. Add a Volume and mount it to `/app/data`.
4. Railway can use the included `railway.json` start command.
5. Set these environment variables:

   `DATA_DIR=/app/data`
   `COOKIE_SECURE=true`

Railway volume docs:
https://docs.railway.com/guides/volumes

## Render

1. Push this project to GitHub.
2. Create a new Web Service from the repo.
3. Use:

   Build command: leave empty
   Start command: `python server.py $PORT`

4. Add a persistent disk and mount it so your database file lives on the disk.
5. Set:

   `DATA_DIR` to the mounted disk path
   `COOKIE_SECURE=true`

Render deploy docs:
https://render.com/docs/deploys/

## Notes

- Without a persistent disk/volume, the SQLite database will reset on redeploy.
- If you want stronger production scaling later, the next upgrade is PostgreSQL.
- I could prepare the deployment files locally, but actual push/deploy still needs your GitHub/Railway/Render account access.
