# Flask REST API

The Flask backend connects to the existing MySQL database and uses the
existing schema, views, triggers, and stored procedures. It does not create
or migrate database objects. API routes are unauthenticated; write endpoints
should only be used in a trusted local or otherwise access-controlled
environment.

## Setup on Windows CMD

Open CMD in the `backend` folder:

```bat
py -3.13 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Set `DB_USER` and `DB_PASSWORD` in the private `.env` file. Do not commit or
share it. `DB_HOST`, `DB_PORT`, and `DB_NAME` default to `127.0.0.1`, `3306`,
and `sports_tournament_management`. Set `FRONTEND_ORIGINS` to the frontend
origin when it differs from `http://localhost:5173`.

Run the API from the `backend` folder:

```bat
python run.py
```

It listens at `http://127.0.0.1:5000` by default. Check readiness with
`curl http://127.0.0.1:5000/api/health`.

## API conventions

- Successful responses use JSON; list routes generally return `{"items": []}`.
- Errors use `{"error": "..."}` and an appropriate 4xx/5xx status.
- SQL values are parameterized. Multi-table operations use transactions.
- Duplicate-value and restricted-delete conflicts return HTTP 409. Invalid
  references, request validation, and trigger/check constraint failures return
  HTTP 400.
- Public read defaults retain published/active filters. Since the service has
  no authentication, `include_unpublished=true` and all write routes are also
  callable by anyone who can reach the API.

## Routes

### Read and existing frontend routes

| Method and route | Description |
|---|---|
| `GET /api/health` | Database connectivity check |
| `GET /api/dashboard/stats` | Dashboard counts |
| `GET /api/students` | Paginated student list; `page`, `per_page` (max 100), `search`, `department_id`, `enrollment_status`, `has_player`, and `sport_id` filters |
| `GET /api/students/<id>` | Student, optional player profile, and sport eligibility |
| `GET /api/sports` | Active sports; `include_inactive=true` includes inactive sports |
| `GET /api/sports/<id>` | Active sport detail; add `include_inactive=true` for inactive sports |
| `GET /api/departments` | Departments |
| `GET /api/teams` | Active teams; `include_inactive=true` includes inactive teams |
| `GET /api/teams/<id>` | Active team and membership history; `include_inactive=true` includes inactive teams/sports; `include_history=false` returns current memberships only |
| `GET /api/players` | Paginated player list; supports `page`, `per_page`, `search`, `sport_id`, and `is_active` |
| `GET /api/players/<id>` | Player and sport eligibility |
| `GET /api/players/<id>/eligibility` | Player's eligibility records |
| `GET /api/tournaments` | Published tournaments; `include_unpublished=true` includes all tournaments |
| `GET /api/tournaments/<id>` | Published tournament and registered participants; add `include_unpublished=true` for administrative details |
| `GET /api/tournaments/<id>/registrations` | Published tournament's registered teams; add `include_unpublished=true` to include all entries/statuses |
| `GET /api/tournaments/<id>/standings` | Existing standings procedure; published tournaments only |
| `GET /api/matches` | Match schedule; optional `tournament_id`, `status`; add `include_unpublished=true` to include all tournaments |
| `GET /api/matches/<id>` | Match details; add `include_unpublished=true` for unpublished tournaments |
| `GET /api/matches/<id>/participants` | Match participant IDs/details, declared outcomes and score segments; unpublished matches require `include_unpublished=true` |
| `GET /api/matches/<id>/results` | Completed-match results and score summary; add `include_unpublished=true` for unpublished tournaments |
| `GET /api/reports/summary` | Player, team, tournament, participant, match, and result counts |
| `GET /api/reports/tournaments/<id>` | Existing report procedure for published tournaments; add `include_unpublished=true` for any tournament |
| `GET /api/reports/match-results` | Completed match results; optional `tournament_id` and `include_unpublished=true` |
| `GET /api/reports/tournament-winners` | First-place entries from completed tournaments' standings; tied first places are retained |

### Write routes

| Method and route | Description |
|---|---|
| `POST /api/students` / `PUT /api/students/<id>` / `DELETE /api/students/<id>` | Create, replace, or delete a student; deletion is rejected while referenced |
| `POST /api/sports` / `PUT /api/sports/<id>` / `DELETE /api/sports/<id>` | Create, update, or delete a sport; referenced sports cannot be deleted |
| `POST /api/students/<id>/player` | Create the student's one-to-one player profile |
| `POST /api/players/<id>/eligibility` | Add eligibility with `sport_id`, `eligible_from`, optional `eligible_to` |
| `PUT /api/players/<id>/eligibility/<sport_id>` | Update eligibility dates; dates cannot exclude existing team memberships |
| `DELETE /api/players/<id>/eligibility/<sport_id>` | End eligibility today; rejected if an existing membership would become invalid |
| `POST /api/teams` / `PUT /api/teams/<id>` / `DELETE /api/teams/<id>` | Create, update, or delete a team; referenced teams cannot be deleted |
| `POST /api/teams/<id>/members` | Add a player; JSON requires `player_id` and may include membership dates |
| `DELETE /api/teams/<id>/members/<player_id>` | End the current membership while retaining its history |
| `POST /api/tournaments` / `PUT /api/tournaments/<id>` | Create/update tournament fields and optional `scoring_rules` |
| `PATCH /api/tournaments/<id>/status` | Change status; use the cancel route to cancel |
| `POST /api/tournaments/<id>/cancel` | Cancel only when there are no live or completed matches; scheduled/postponed fixtures are marked cancelled |
| `POST /api/tournaments/<id>/teams` | Register a team using `{"team_id": 1}` |
| `POST /api/matches` | Create a match and add its registered `entry_ids` in one transaction |
| `PUT /api/matches/<id>` | Update schedule, venue, stage, round, or status |
| `PATCH /api/matches/<id>/status` | Change match status; completion must go through results |
| `PUT /api/matches/<id>/scores` | Upsert score segments for match participants |
| `PUT /api/matches/<id>/results` | Record every participant's outcome and optionally scores, then complete the match atomically |

Tournament JSON uses the existing columns: `sport_id`, `name`,
`competition_format` (`team` or `individual`), `season`, `start_date`,
`end_date`, optional `status`, `is_published`, `description`, and optional
`scoring_rules` (`points_for_win`, `points_for_draw`, `points_for_loss`).
Dates use `YYYY-MM-DD`; match times accept ISO date/time strings. Team match
results require either one `win` and one `loss`, or two `draw` outcomes.
Every match participant must receive one result. Individual tournaments may
use `result_rank`; ties are allowed by the schema.

Example score/result request:

```json
{
  "results": [
    {"entry_id": 10, "outcome": "win"},
    {"entry_id": 11, "outcome": "loss"}
  ],
  "scores": [
    {"entry_id": 10, "segment_number": 1, "numeric_value": 2},
    {"entry_id": 11, "segment_number": 1, "numeric_value": 1}
  ]
}
```

## Schema limitations

The existing schema has no registration-deadline or maximum-capacity columns.
Team registration is allowed only while tournament status is `registration`
and before `start_date`; a per-tournament capacity cannot be enforced without
a schema change. Matches have no duration/end-time, so conflict validation
rejects another scheduled/live match for the same team at the exact same
`scheduled_at` timestamp; it cannot infer arbitrary time-interval overlap.
Only team tournament registration is implemented; individual entry creation
is not part of this API expansion.

The schema has no tournament champion field or final-round marker. The winners
report therefore identifies the first-place entry or tied entries from
published tournaments whose status is `completed`, rather than guessing a
champion from an arbitrary match win.

## Tests

Run mocked backend tests from this folder:

```bat
python -m unittest discover -s tests -v
```

These tests do not write to the configured MySQL database. Database reads can
be smoke-tested after setting `.env`, but no live write test should use the
existing project/sample records.

### Isolated Phase 8 MySQL workflow

After provisioning `sports_tournament_management_phase8_test`, run the
real-MySQL workflow test from this folder:

```bat
set DB_NAME=sports_tournament_management_phase8_test
set RUN_PHASE8_INTEGRATION=1
.\.venv\Scripts\python.exe -m unittest tests.test_phase8_integration -v
```

The test refuses to run unless `DB_NAME` is exactly the isolated database and
checks `SELECT DATABASE()` on every MySQL connection before application SQL.
It creates uniquely named records and intentionally retains them; it does not
clean up test data. Never point it at `sports_tournament_management`.
