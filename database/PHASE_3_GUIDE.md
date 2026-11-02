# Phase 3: Advanced DBMS

These files target the existing MySQL 8.0.46 database. They add views,
procedures, and triggers only; the 15-table schema and existing records are
unchanged. SQL has not been executed as part of this work.

> **Do not rerun `sample_data.sql` for Phase 3.** Its current apply flag is
> `1`, and running it would attempt sample-data inserts.

## What is included

- `views.sql`: published tournaments, participants, match schedule, completed
  results, and dynamic standings. Team points use configured rules or 3/1/0
  defaults. Individual standings use best (lowest) result rank; equal ranks
  tie. Scheduled matches do not count. No standings table is added.
- `procedures.sql`: `sp_get_tournament_standings` and
  `sp_get_tournament_report`.
- `triggers.sql`: insert/update checks for tournament-entry format/sport,
  same-tournament match participants, and team membership sport eligibility.
  Existing foreign keys and CHECK constraints continue to validate row-level
  rules.
- `transactions.sql`: one manual transaction example for recording a
  two-entry match result. It is not an installation script.
- `indexes_review.md`: concise source-schema index review; no new indexes
  are recommended without live `EXPLAIN` evidence.

## Execution order

Run each command separately from **Windows CMD**. The project directory on
this machine has two spaces between `Tournament` and `management`; preserve
that spelling in the paths. MySQL prompts for the password—do not put it in
the command.

1. Install views:

   ```bat
   "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p sports_tournament_management < "C:\Users\shubham\OneDrive\Projects\Sport and Tournament  management system\Sport-and-Tournament-Management-System\database\views.sql"
   ```

2. Install procedures:

   ```bat
   "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p sports_tournament_management < "C:\Users\shubham\OneDrive\Projects\Sport and Tournament  management system\Sport-and-Tournament-Management-System\database\procedures.sql"
   ```

3. Install triggers during a brief pause in application writes:

   ```bat
   "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p sports_tournament_management < "C:\Users\shubham\OneDrive\Projects\Sport and Tournament  management system\Sport-and-Tournament-Management-System\database\triggers.sql"
   ```

These are DDL scripts. MySQL DDL is not transactional; if a script fails
while replacing objects, inspect the objects before continuing.

## Verify the installed objects

Use an existing published tournament ID instead of `1`:

```sql
SHOW FULL TABLES LIKE 'vw_%';
SHOW PROCEDURE STATUS
WHERE Db = 'sports_tournament_management';
SHOW TRIGGERS;

SELECT * FROM vw_published_tournaments;
SELECT * FROM vw_tournament_participants;
SELECT * FROM vw_match_schedule;
SELECT * FROM vw_completed_match_results;
SELECT *
FROM vw_tournament_standings
WHERE tournament_id = 1
ORDER BY standings_rank, entry_id;

CALL sp_get_tournament_standings(1);
CALL sp_get_tournament_report(1);
```

Public database accounts should receive access only to appropriate public
views. The report procedure exposes unpublished tournament information and
should be restricted to administrators. Procedures use `SQL SECURITY
INVOKER`, so callers need the corresponding `SELECT` privileges.

## Transaction demonstration

Do not run `transactions.sql` unchanged: replace its zero IDs and score
values. Use a real match with exactly two entries and run it in one
interactive MySQL connection. Before inserting, verify the `SELECT` shows the
intended scheduled/live match and exactly the intended two entries. Execute
the inserts and status update in order. Commit only if every statement
succeeds and the final status is `completed`; on any error or mismatch, stop
and issue `ROLLBACK;` in the same connection.

Open the connection from CMD:

```bat
"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p sports_tournament_management
```

In that connection, first run the two read-only `SELECT` checks from the file
after setting the intended IDs. Confirm the match is scheduled/live and that
the only entries returned are the two selected IDs. Then run the edited file:

```sql
SOURCE "C:\Users\shubham\OneDrive\Projects\Sport and Tournament  management system\Sport-and-Tournament-Management-System\database\transactions.sql";
```

The script intentionally leaves the transaction open; issue `COMMIT;` or
`ROLLBACK;` manually after reviewing the final status.

The transaction example is illustrative, not a general match-finalization
API. It handles one numeric score segment per entry; multi-entry matches,
multiple segments, and corrections should be implemented as backend
transactions.

## Indexes and limitations

`indexes_review.md` summarizes the indexes already in `schema.sql`; it does
not propose schema changes. The views derive data from current results.
Individual tournaments have no configured points formula, so their standings
show rank and outcome counts rather than points. Sport-specific minimum
participant counts and overlapping active memberships remain backend
transaction responsibilities.
