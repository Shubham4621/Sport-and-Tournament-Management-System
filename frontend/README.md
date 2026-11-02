# SportsDesk frontend

React + Vite frontend for the existing Flask API. No login or authentication
screens are included. The API base URL defaults to
`http://127.0.0.1:5000/api`.

## Run locally (Windows CMD)

Start the Flask backend in a separate terminal first. The backend loads its
database settings from `backend\.env` and listens at
`http://127.0.0.1:5000`.

Then run:

```bat
cd /d "C:\Users\shubham\OneDrive\Projects\Sport and Tournament  management system\Sport-and-Tournament-Management-System\frontend"
npm install
npm run dev
```

Open the Vite URL shown in the terminal (normally `http://127.0.0.1:5173`).
Flask CORS already allows that default origin. For a different frontend or API
address, set `FRONTEND_ORIGINS` in the backend environment and
`VITE_API_URL` in a local frontend `.env` file.

## Production build

```bat
npm run build
npm run preview
```

## Implemented views

- Dashboard summary cards and recent published tournament/fixture lists.
- Active sports catalog.
- Student search, paging, add, view, and edit forms.
- Active teams with sport and department information.
- Published tournament list, participant details, and standings navigation.
- Published match schedule, tournament/status filters, match details, and
  declared result display.
- Tournament standings from the existing database procedure.

The current API does not expose team roster members, create/edit sports or
teams/tournaments/matches, or return totals for unpublished tournaments and
fixtures. The frontend does not invent these operations or data.
