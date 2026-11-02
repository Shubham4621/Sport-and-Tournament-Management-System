# Phase 8.3 End-to-End Test Report

## Result

The opt-in integration workflow passed against
`sports_tournament_management_phase8_test` using MySQL 8.0.46. It ran through
Flask's test client and made real MySQL reads and writes. The original
`sports_tournament_management` database was not selected or modified.

## Workflow and API results

| Workflow stage | Endpoint(s) | Result |
|---|---|---|
| Create sport and students/player profiles | `POST /api/sports`, `POST /api/students`, `POST /api/students/<id>/player` | Passed; created unique run-specific records. |
| Set eligibility, create teams, add members | `POST /api/players/<id>/eligibility`, `POST /api/teams`, `POST /api/teams/<id>/members` | Passed for eligible players. An ineligible membership was rejected without a membership row. |
| Create tournament and register teams | `POST /api/tournaments`, `POST /api/tournaments/<id>/teams` | Passed. Duplicate registration returned 409 without changing the entry count; wrong-sport registration was rejected. |
| Schedule match | `POST /api/matches` | Passed for two registered entries. A participant from another tournament was rejected without a match row; duplicate match number returned 409 without extra match or entry rows. |
| Save scores and declare result | `PUT /api/matches/<id>/scores`, `PUT /api/matches/<id>/results` | Passed for two scores and a win/loss result. An invalid two-winner result returned 400 and left the match scheduled with no result rows; successful declaration saved both results and completed the match. |
| Verify standings and reports | `GET /api/tournaments/<id>/standings`, `GET /api/reports/tournaments/<id>`, `GET /api/reports/match-results`, `GET /api/matches/<id>/results`, `PATCH /api/tournaments/<id>/status`, `GET /api/reports/tournament-winners`, `GET /api/reports/summary` | Passed. Verified win/loss totals, played matches, 3/0 points, persisted scores/results, report totals, and winner identification after completing the tournament. |
| Verify dashboard and persisted database state | `GET /api/dashboard/stats` plus guarded read-only SQL assertions | Passed. Dashboard deltas matched this run's workflow records. |

Additional database-boundary checks passed: a nonexistent sport foreign key
was rejected by MySQL with error 1452, and a wrong-sport tournament entry was
rejected by its trigger with error 1644. Rejected operations were checked for
partial rows; no partial match, membership, registration, or result writes
remained.

## Test execution

- Real-MySQL integration suite: **1 passed** (`test_complete_real_mysql_workflow_and_rejections`).
- Existing backend suite: **22 passed**; the integration test is opt-in and
  skipped during the normal mocked suite unless explicitly enabled.
- Frontend production build (`npm run build`): **passed**.
- No SQL script or frontend browser interaction was executed as an end-to-end
  test. Frontend verification was the production build only.

During development, earlier integration attempts exposed test assertion
assumptions about MySQL trigger exceptions and numeric values in API JSON.
The assertions were corrected to recognize connector database errors and
normalize numeric values; the final real-MySQL workflow then passed. Expected
database errors from deliberately invalid cases can appear in Flask logs.

## Database isolation and retained records

Before each application write, the test runs `SELECT DATABASE()` and requires
the exact isolated database name. Every connector call is patched with an
additional guard that rejects the original database and verifies the selected
schema. Direct foreign-key and trigger checks use the same guarded connector
and roll back their intentionally invalid transactions.

The test uses unique run-specific names and does not delete its records or the
test database. Earlier development attempts also left some incomplete test
records in that isolated schema. The last read-only inventory reported 6
sports, 9 students, 9 players, 6 player-sport associations, 9 teams, 6 team
memberships, 5 tournaments, 3 scoring-rule rows, 8 tournament entries, 2
matches, 4 match entries, 4 scores, and 4 results. These are accumulated test
data, not the counts created by the final successful run alone.

No workflow writes were directed to `sports_tournament_management`; no
production records or schema objects were changed. No automatic cleanup was
performed.

## Remaining limitations

- The test covers the team-tournament workflow, not individual-tournament
  registration.
- It does not automate React/browser operations, CORS preflight, or UI refresh
  behavior.
- The schema has no maximum-registration-capacity field, so capacity
  enforcement cannot be exercised.
- Test records remain in the isolated database and should be retained unless
  cleanup is separately approved.
