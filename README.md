# Club Membership

A small Flask app for managing club membership, with manager, staff and
student roles. No database — data lives in Python lists in `app.py`, so it
resets whenever the app restarts.

## Run locally

    pip install -r requirements.txt
    python app.py

Then open http://localhost:5000

Demo accounts:
- manager / manager123
- staff / staff123
- student / student123

## Deploy on Railway

1. Push this folder to a GitHub repo and create a new Railway project from it
   (or run `railway init` then `railway up` from inside this folder with the
   Railway CLI).
2. Railway auto-detects Python via Nixpacks and installs `requirements.txt`.
   The included `Procfile` tells it to start the app with:
       gunicorn app:app
3. In the Railway project's **Variables** tab, set:
   - `SECRET_KEY` — any random string (used to sign the session cookie).
   Railway sets `PORT` automatically; `app.py` already reads it.
4. Deploy. Railway gives you a public `*.up.railway.app` URL.

Note: since there's no database, every redeploy or restart wipes any
accounts, clubs, or registrations added after the app started — everything
resets back to the three demo accounts and three demo clubs.

## What's new

- Joining a club now creates a **pending** request with the date it was
  made, instead of joining instantly.
- Staff (and managers) can **accept** or **reject** pending requests from
  their dashboard. A rejected student can request again.
- Registration tables now show the request date and status everywhere.

## Activity log

Managers get an **Activity log** page (link in the dashboard header). It records
sign-ins, accounts, clubs, join requests, roles and coordinator changes, and keeps
a short snapshot of anything that was deleted. Filter it by Deleted, Accounts,
Clubs, Requests, Roles or Sign-ins. Activity by or about the demo staff and demo
student accounts is not logged (set `LOG_DEMO_ACTIVITY=1` to include it).

Timestamps use UTC by default. Set an `APP_TIMEZONE` variable (a name such as
`America/New_York`) to change that. Like everything else, the log lives in
memory and resets when the app restarts.
