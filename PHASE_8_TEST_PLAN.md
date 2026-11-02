# Phase 8: Safe End-to-End Test Plan

## Purpose and safety boundary

This plan verifies the complete React/Flask/MySQL workflow without changing
the existing `sports_tournament_management` database. **No end-to-end write
tests have been executed.** The current application has no authentication, so
the test backend and frontend must bind to loopback/private interfaces and must
not be exposed to a shared network.

The plan uses fresh, uniquely named test records in an isolated MySQL instance.
It does not use or overwrite project sample records. Do not run these workflow
steps against the existing project database.

## Test environment isolation

### Separate test database on the configured MySQL server

Use the isolated setup helper at `backend/scripts/setup_phase8_test_db.py`.
It targets only `sports_tournament_management_phase8_test`, rewrites the
source scripts' fixed `USE sports_tournament_management` directive in memory,
does not edit SQL files, and never loads `sample_data.sql`.

First run the helper without arguments. This validates/parses setup SQL and
does not connect to MySQL:

```bat
cd backend
.\.venv\Scripts\python.exe scripts\setup_phase8_test_db.py
```

For actual isolated setup, configure `DB_HOST`, `DB_PORT`, `DB_USER`, and
`DB_PASSWORD` in the local backend environment or `backend/.env`. Credentials
must remain private. The helper ignores `DB_NAME`, connects without a default
database, and requires permission to create a database and its objects. Run
the explicit creation command:

```bat
.\.venv\Scripts\python.exe scripts\setup_phase8_test_db.py --create
```

The helper refuses if the test database already exists. On a fresh target it
creates `sports_tournament_management_phase8_test`, applies `schema.sql`,
`views.sql`, `procedures.sql`, and `triggers.sql` in order, and inserts one
test-only department fixture because teams require a department and there is
no department write API. It verifies 15 empty tables, 5 views, 2 procedures,
6 triggers, and the fixture. No project/sample records are copied. Because DDL
can implicitly commit, a partial failure leaves the isolated target for
inspection; the helper never drops it automatically.

For Flask, set `DB_NAME=sports_tournament_management_phase8_test` in the
backend process environment and start it on loopback. Check `/api/health`
before any workflow write. Set frontend `VITE_API_URL` to that local API. The
project database and `.env` remain unchanged. Preserve the test database
until results are reviewed; cleanup requires separate approval. Caller-side
rollback cannot undo API requests because each request commits its own
connection.

#### Setup verification completed

The helper was run with `--create` against the configured MySQL server. It
created the separate test database and verified MySQL 8.0.46, 15 tables, 5
views, 2 procedures, 6 triggers, zero rows in application tables, and exactly
one test department fixture. Flask was then configured in-process with
`DB_NAME=sports_tournament_management_phase8_test`; `SELECT DATABASE()` and
10 read-only API GETs confirmed the selected database and successful
connection. Dashboard counts were all zero. No workflow API POST/PUT/PATCH
requests or end-to-end write tests were run. The existing project database
was not selected by the setup script.

## End-to-end workflow

Use the React UI where it covers the operation and confirm the corresponding
request/response in browser network tools. For API assertions, use the actual
routes below and JSON bodies. All values such as IDs and unique names are
placeholders populated from previous responses.

| # | Operation and endpoint | Request / preconditions | Expected result |
|---|---|---|---|
| 0 | Preflight: `GET /api/health`, `GET /api/departments` | Confirm local backend is connected to the isolated database; record the test department ID created during setup. | Health succeeds. The test database contains only the setup department before the workflow. No project sample records appear. |
| 1 | Create sport: `POST /api/sports` | `{"name":"E2E <run-id> Sport","description":"Isolated Phase 8 test","is_active":true}` | HTTP 201; one new `Sports` row with a new `sport_id`. Record that ID. A duplicate unique name should be rejected without a second row. |
| 2 | Create student: `POST /api/students` | `{"student_number":"E2E-<run-id>","first_name":"E2E","last_name":"Player","email":null,"department_id":<test-department-id>,"enrollment_status":"active"}` | HTTP 201; one `Students` row. Record `student_id`. Student number is unique. |
| 3 | Create player profile: `POST /api/students/<student_id>/player` | `{"is_active":true}` | HTTP 201; exactly one `Players` row referencing the student. A repeated request must not create another player because `Players.student_id` is unique. Record `player_id`. |
| 4 | Associate player with sport: `POST /api/players/<player_id>/eligibility` | `{"sport_id":<sport_id>,"eligible_from":"<today>","eligible_to":null}`. Sport must be active. | HTTP 201; one `Player_Sports` row for this player/sport. Dates satisfy the CHECK constraint. |
| 5 | Create team(s): `POST /api/teams` | Create the primary team with `{"sport_id":<sport_id>,"department_id":<test-department-id>,"name":"E2E <run-id> Team A","team_code":"E2E-A","is_active":true}`. Create a second team with a distinct name/code for the same sport/department. | Each request returns HTTP 201 and a different `team_id`; two `Teams` rows reference the test sport and department. **The second team is required**: a team match cannot be scheduled with only one registered participant. |
| 6 | Add player to primary roster: `POST /api/teams/<team_a_id>/members` | `{"player_id":<player_id>,"membership_from":"<today>","membership_to":null}`. The player's eligibility must cover the membership and match the team's sport. | HTTP 201; one `Team_Memberships` row. `GET /api/teams/<team_a_id>?include_inactive=true` returns the player in `members`. |
| 7 | Create tournament: `POST /api/tournaments` | `{"sport_id":<sport_id>,"name":"E2E <run-id> Cup","competition_format":"team","season":"<run-id>","start_date":"<future-date>","end_date":"<later-future-date>","status":"registration","is_published":true,"description":"Isolated Phase 8 test","scoring_rules":{"points_for_win":3,"points_for_draw":1,"points_for_loss":0}}`. Dates must be ordered; start must be after today for registration. | HTTP 201; one `Tournaments` row plus one `Tournament_Scoring_Rules` row. Record `tournament_id`. Publication and active sport are required for the standings procedure/views. |
| 8 | Register both teams: `POST /api/tournaments/<tournament_id>/teams` | Send `{"team_id":<team_a_id>}` and then `{"team_id":<team_b_id>}`. | Each returns HTTP 201; two `Tournament_Entries` rows with `status='registered'`. Same-sport, team-format, registration status, future start date, and uniqueness rules pass. Re-registering a team returns a conflict and leaves the entry count unchanged. |
| 9 | Schedule match: `POST /api/matches` | `{"tournament_id":<tournament_id>,"match_number":1,"entry_ids":[<entry_a_id>,<entry_b_id>],"scheduled_at":"<future-datetime>","stage":"Final","round_name":"Final","venue":"Test Venue"}`. Use the returned entry IDs and two distinct entries from this tournament. | HTTP 201; one scheduled `Matches` row and exactly two `Match_Entries` rows. Both entries must belong to this tournament. Avoid reusing the exact same team/time in another scheduled/live match. Record `match_id`. |
| 10 | Add scores: `PUT /api/matches/<match_id>/scores` | `{"scores":[{"entry_id":<entry_a_id>,"segment_number":1,"segment_label":"Test segment","numeric_value":2.0,"text_value":null},{"entry_id":<entry_b_id>,"segment_number":1,"segment_label":"Test segment","numeric_value":1.0,"text_value":null}]}`. Provide exactly one of `numeric_value` or `text_value` per score. | HTTP 200; `scores_saved` is 2. Two `Match_Scores` rows exist and match their participants. Match remains not completed until result declaration. |
| 11 | Declare result and complete: `PUT /api/matches/<match_id>/results` | `{"results":[{"entry_id":<entry_a_id>,"outcome":"win","result_rank":null,"official_note":"E2E result"},{"entry_id":<entry_b_id>,"outcome":"loss","result_rank":null,"official_note":"E2E result"}]}` | HTTP 200; both `Match_Results` rows are written and `Matches.status` becomes `completed` atomically. A team match requires exactly two participants and one win plus one loss, or two draws. |
| 12 | Verify match/standings: `GET /api/matches/<match_id>/results?include_unpublished=true`, `GET /api/tournaments/<tournament_id>/standings` | The match/tournament may be queried administratively; the standings procedure additionally requires the tournament to be published and its sport active. | Two result rows and two standings rows. The winner has 1 played, 1 win, 0 losses, 0 draws, and 3 points; the other entry has 1 played, 0 wins, 1 loss, 0 draws, and 0 points. Match is not counted before completion. |
| 13 | Verify dashboard/reports: `GET /api/dashboard/stats`, `GET /api/reports/summary`, `GET /api/reports/tournaments/<tournament_id>?include_unpublished=true`, `GET /api/reports/match-results?tournament_id=<tournament_id>&include_unpublished=true` | Compare counts against the isolated database before and after the workflow. The tournament report uses `sp_get_tournament_report`; match-results report returns one row per participant result. | Dashboard and summary counts increase by the test rows; tournament report shows 2 entries, 1 total/completed match, and 2 declared results; match-results returns 2 rows. |
| 14 | Optional tournament winner report: `PATCH /api/tournaments/<tournament_id>/status` | Send `{"status":"completed"}` only after the completed-match checks; then request `GET /api/reports/tournament-winners`. | The winner report is eligible to include the tournament only after tournament status is `completed`; it reports the first-place standings entry (or tied first-place entries). This status change is separate from completing the match. |

### Read-only database assertions

Run these only on the isolated test instance after the API workflow. Substitute
the recorded test IDs; these are verification SELECTs, not scripts to run
against the project database.

```sql
SELECT sport_id, name, is_active FROM Sports WHERE sport_id = <sport_id>;
SELECT student_id, student_number FROM Students WHERE student_id = <student_id>;
SELECT player_id, student_id FROM Players WHERE player_id = <player_id>;
SELECT player_id, sport_id, eligible_from, eligible_to
FROM Player_Sports WHERE player_id = <player_id> AND sport_id = <sport_id>;
SELECT team_id, sport_id, department_id, name FROM Teams
WHERE team_id IN (<team_a_id>, <team_b_id>);
SELECT team_id, player_id, membership_from, membership_to
FROM Team_Memberships WHERE team_id = <team_a_id> AND player_id = <player_id>;
SELECT tournament_id, sport_id, competition_format, status, is_published
FROM Tournaments WHERE tournament_id = <tournament_id>;
SELECT tournament_id, points_for_win, points_for_draw, points_for_loss
FROM Tournament_Scoring_Rules WHERE tournament_id = <tournament_id>;
SELECT entry_id, tournament_id, team_id, status FROM Tournament_Entries
WHERE tournament_id = <tournament_id>;
SELECT match_id, tournament_id, status FROM Matches WHERE match_id = <match_id>;
SELECT match_id, entry_id FROM Match_Entries WHERE match_id = <match_id>;
SELECT match_id, entry_id, segment_number, numeric_value, text_value
FROM Match_Scores WHERE match_id = <match_id>;
SELECT match_id, entry_id, outcome, result_rank FROM Match_Results
WHERE match_id = <match_id>;
```

## Existing automated coverage

The existing backend suite uses Python `unittest` and mocks database
operations. It does **not** make writes to MySQL. Current tests cover:

- Sport creation parameterization and invalid sport input.
- Student creation/validation and paginated student filters.
- Tournament creation with publication and scoring rules, partial date update,
  status/cancellation validation, and standings procedure invocation.
- Registration request validation and rejection of a team whose sport differs
  from the tournament.
- Match rejection when entries do not belong to the requested tournament.
- Participant lookup returning scores.
- Atomic result declaration at the application-call level, plus transaction
  commit and rollback behavior in the database helper.
- Route registration without authentication; health and dashboard are
  accessible without a bearer token.

These are useful unit-level checks, not proof that MySQL constraints, triggers,
views, procedures, connector behavior, frontend forms, or the full workflow
work together against a real database.

## Missing coverage and integration risks

1. **No safe full-flow MySQL integration test exists.** Current tests mock SQL;
   none proves that all workflow operations commit correctly on MySQL 8.0.46.
2. **No existing department write API.** Team creation requires a department,
   so the test database needs the one-time setup fixture described above.
3. **Two teams are mandatory for the requested team match.** One team created
   and registered alone cannot satisfy the match's minimum two-participant
   requirement. The test creates a second team and registers it.
4. **No registration-capacity field or enforcement exists.** The schema has no
   maximum-capacity column. Registration closes at `start_date`; a registration
   deadline separate from the start date is not supported.
5. **No individual-tournament registration API exists.** This plan tests a team
   tournament; individual entry creation is outside this workflow/API.
6. **Publication and sport activity affect public data.** Standings use a
   stored procedure that rejects tournaments not visible through
   `vw_published_tournaments`, which requires a published tournament and active
   sport. Use `is_published=true` and an active test sport.
7. **Match completion and tournament completion are distinct.** Results mark a
   match completed; the tournament-winners report filters tournaments whose
   own status is completed. Do not expect a winner-report row before the
   explicit tournament-status step.
8. **Database scripts hard-code the production-named schema.** Use a separate
   MySQL instance/port as described; do not rely on an alternate database name
   alone.
9. **The application has no authentication.** Keep both test servers local
   and use only disposable test data.
10. **UI plus API assertions are both needed.** Unit tests do not exercise
    React forms, response refresh behavior, API CORS, or actual MySQL error
    responses for duplicate keys, foreign keys, and trigger signals.

## Execution gate

This document is a plan only. Before a later end-to-end test run, verify the
test database host/port and database name independently, confirm the frontend
uses the local test API, and obtain approval to execute writes against that
disposable instance. If isolation is uncertain, do not proceed. No SQL or API
write operations have been run as part of preparing this plan.
