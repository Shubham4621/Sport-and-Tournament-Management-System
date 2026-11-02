-- Fictional Phase 2 sample data for MySQL 8.0.16+.
-- No administrator credentials or plaintext passwords are inserted.
-- This script never deletes, truncates, or updates existing records.
--
-- SAFETY: Run once with @apply_sample_data = 1 to inspect counts, IDs, and
-- name collisions. Student identity mismatches are reported and force a
-- SQL error before insertion. After reviewing the output, change the next
-- assignment to 1 and run again to insert only missing sample rows.
-- Re-running with the flag enabled is idempotent for these sample keys.
-- If any statement errors during insertion, stop and issue ROLLBACK in the
-- same Workbench connection before retrying.

USE sports_tournament_management;
SET NAMES utf8mb4;
SET @apply_sample_data := 1;

-- Read-only preflight: current data counts.
SELECT 'Admins' AS table_name, COUNT(*) AS row_count FROM Admins
UNION ALL SELECT 'Sports', COUNT(*) FROM Sports
UNION ALL SELECT 'Departments', COUNT(*) FROM Departments
UNION ALL SELECT 'Students', COUNT(*) FROM Students
UNION ALL SELECT 'Players', COUNT(*) FROM Players
UNION ALL SELECT 'Player_Sports', COUNT(*) FROM Player_Sports
UNION ALL SELECT 'Teams', COUNT(*) FROM Teams
UNION ALL SELECT 'Team_Memberships', COUNT(*) FROM Team_Memberships
UNION ALL SELECT 'Tournaments', COUNT(*) FROM Tournaments
UNION ALL SELECT 'Tournament_Scoring_Rules', COUNT(*) FROM Tournament_Scoring_Rules
UNION ALL SELECT 'Tournament_Entries', COUNT(*) FROM Tournament_Entries
UNION ALL SELECT 'Matches', COUNT(*) FROM Matches
UNION ALL SELECT 'Match_Entries', COUNT(*) FROM Match_Entries
UNION ALL SELECT 'Match_Scores', COUNT(*) FROM Match_Scores
UNION ALL SELECT 'Match_Results', COUNT(*) FROM Match_Results
ORDER BY table_name;

-- Existing department IDs are discovered rather than assumed. The first four
-- are used for sample teams; all existing department records are preserved.
SELECT department_id, department_name
FROM Departments
ORDER BY department_id;

-- Read-only collision check for requested catalog data and this script's
-- uniquely prefixed student, team, and tournament records.
SELECT sport_id, name AS existing_requested_sport, is_active
FROM Sports
WHERE name IN (
    'Cricket', 'Football', 'Volleyball', 'Kabaddi', 'Badminton', 'Chess',
    'Basketball', 'Athletics'
)
ORDER BY name;

SELECT COUNT(*) AS sample_student_identity_candidates
FROM Students
WHERE student_number LIKE 'P2-SAMPLE-%'
   OR email LIKE 'p2.sample.%@example.invalid';

-- A sample student identity is valid only when both unique values match the
-- expected pair. On mismatch, report a count and deliberately raise a
-- read-only SQL error before the transaction; all inserts are also gated off.
SELECT COUNT(*) INTO @sample_identity_conflict_count
FROM (
    SELECT 'P2-SAMPLE-001' AS student_number, 'p2.sample.001@example.invalid' AS email
    UNION ALL SELECT 'P2-SAMPLE-002', 'p2.sample.002@example.invalid'
    UNION ALL SELECT 'P2-SAMPLE-003', 'p2.sample.003@example.invalid'
    UNION ALL SELECT 'P2-SAMPLE-004', 'p2.sample.004@example.invalid'
    UNION ALL SELECT 'P2-SAMPLE-005', 'p2.sample.005@example.invalid'
    UNION ALL SELECT 'P2-SAMPLE-006', 'p2.sample.006@example.invalid'
    UNION ALL SELECT 'P2-SAMPLE-007', 'p2.sample.007@example.invalid'
    UNION ALL SELECT 'P2-SAMPLE-008', 'p2.sample.008@example.invalid'
    UNION ALL SELECT 'P2-SAMPLE-009', 'p2.sample.009@example.invalid'
    UNION ALL SELECT 'P2-SAMPLE-010', 'p2.sample.010@example.invalid'
    UNION ALL SELECT 'P2-SAMPLE-011', 'p2.sample.011@example.invalid'
    UNION ALL SELECT 'P2-SAMPLE-012', 'p2.sample.012@example.invalid'
) AS expected
JOIN Students existing
  ON existing.student_number = expected.student_number
  OR existing.email = expected.email
WHERE NOT (
    existing.student_number <=> expected.student_number
    AND existing.email <=> expected.email
);

SELECT 'sample_student_identity_conflicts' AS check_name,
       @sample_identity_conflict_count AS conflict_count;

SET @sample_identity_guard_sql := IF(
    @sample_identity_conflict_count > 0,
    'SELECT * FROM `P2_SAMPLE_IDENTITY_CONFLICT_STOP`',
    'SELECT 1'
);
PREPARE sample_identity_guard FROM @sample_identity_guard_sql;
EXECUTE sample_identity_guard;
DEALLOCATE PREPARE sample_identity_guard;

SELECT p.player_id, p.student_id, s.student_number, p.is_active
FROM Players p
JOIN Students s ON s.student_id = p.student_id
WHERE s.student_number LIKE 'P2-SAMPLE-%'
  AND s.email = CONCAT(
      'p2.sample.',
      RIGHT(s.student_number, 3),
      '@example.invalid'
  )
ORDER BY s.student_number;

SELECT ps.player_id, s.student_number, ps.sport_id, sp.name AS sport_name,
       ps.eligible_from, ps.eligible_to
FROM Player_Sports ps
JOIN Players p ON p.player_id = ps.player_id
JOIN Students s ON s.student_id = p.student_id
JOIN Sports sp ON sp.sport_id = ps.sport_id
WHERE s.student_number LIKE 'P2-SAMPLE-%'
  AND s.email = CONCAT(
      'p2.sample.',
      RIGHT(s.student_number, 3),
      '@example.invalid'
  )
ORDER BY s.student_number, sp.name;

SELECT team.team_id, team.sport_id, sp.name AS sport_name,
       team.department_id, d.department_name, team.name
FROM Teams team
JOIN Sports sp ON sp.sport_id = team.sport_id
JOIN Departments d ON d.department_id = team.department_id
WHERE team.name LIKE 'P2 Sample %'
ORDER BY team.name, team.team_id;

SELECT tm.team_id, team.name AS team_name, tm.player_id,
       s.student_number, tm.membership_from, tm.membership_to
FROM Team_Memberships tm
JOIN Teams team ON team.team_id = tm.team_id
JOIN Players p ON p.player_id = tm.player_id
JOIN Students s ON s.student_id = p.student_id
WHERE team.name LIKE 'P2 Sample %'
   OR (
       s.student_number LIKE 'P2-SAMPLE-%'
       AND s.email = CONCAT(
           'p2.sample.',
           RIGHT(s.student_number, 3),
           '@example.invalid'
       )
   )
ORDER BY team.name, s.student_number, tm.membership_from;

SELECT tournament_id, sport_id, name, competition_format, season,
       status, is_published
FROM Tournaments
WHERE name LIKE 'Phase 2 Sample %'
ORDER BY name;

SELECT rules.tournament_id, t.name AS tournament_name,
       rules.points_for_win, rules.points_for_draw, rules.points_for_loss
FROM Tournament_Scoring_Rules rules
JOIN Tournaments t ON t.tournament_id = rules.tournament_id
WHERE t.name LIKE 'Phase 2 Sample %'
ORDER BY t.name;

SELECT te.entry_id, te.tournament_id, t.name AS tournament_name,
       te.team_id, te.player_id, te.status
FROM Tournament_Entries te
JOIN Tournaments t ON t.tournament_id = te.tournament_id
WHERE t.name LIKE 'Phase 2 Sample %'
ORDER BY t.name, te.entry_id;

SELECT m.match_id, m.tournament_id, t.name AS tournament_name,
       m.match_number, m.status
FROM Matches m
JOIN Tournaments t ON t.tournament_id = m.tournament_id
WHERE t.name LIKE 'Phase 2 Sample %'
ORDER BY t.name, m.match_number;

SELECT me.match_id, me.entry_id, t.name AS tournament_name,
       m.match_number, te.team_id, te.player_id
FROM Match_Entries me
JOIN Matches m ON m.match_id = me.match_id
JOIN Tournaments t ON t.tournament_id = m.tournament_id
JOIN Tournament_Entries te ON te.entry_id = me.entry_id
WHERE t.name LIKE 'Phase 2 Sample %'
ORDER BY t.name, m.match_number, me.entry_id;

SELECT score.match_id, score.entry_id, score.segment_number,
       score.numeric_value, score.text_value
FROM Match_Scores score
JOIN Matches m ON m.match_id = score.match_id
JOIN Tournaments t ON t.tournament_id = m.tournament_id
WHERE t.name LIKE 'Phase 2 Sample %'
ORDER BY t.name, m.match_number, score.entry_id, score.segment_number;

SELECT result_row.*
FROM Match_Results result_row
JOIN Matches m ON m.match_id = result_row.match_id
JOIN Tournaments t ON t.tournament_id = m.tournament_id
WHERE t.name LIKE 'Phase 2 Sample %'
ORDER BY t.name, m.match_number, result_row.entry_id;

-- Confirm that the installed schema has the required result_rank column.
-- If only legacy `rank` exists, stop and resolve the schema mismatch in
-- Workbench before changing @apply_sample_data to 1.
SELECT
    SUM(column_name = 'result_rank') > 0 AS result_rank_present,
    SUM(column_name = 'rank') > 0 AS legacy_rank_present
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'Match_Results'
  AND column_name IN ('rank', 'result_rank');

-- Resolve existing department IDs only after preflight is displayed.
SET @department_1 := (
    SELECT department_id FROM Departments ORDER BY department_id LIMIT 0, 1
);
SET @department_2 := (
    SELECT department_id FROM Departments ORDER BY department_id LIMIT 1, 1
);
SET @department_3 := (
    SELECT department_id FROM Departments ORDER BY department_id LIMIT 2, 1
);
SET @department_4 := (
    SELECT department_id FROM Departments ORDER BY department_id LIMIT 3, 1
);

START TRANSACTION;

-- Sports are matched by their unique names; existing rows are not changed.
INSERT INTO Sports (name, description, is_active)
SELECT sample.name, sample.description, TRUE
FROM (
    SELECT 'Cricket' AS name, 'College cricket competition.' AS description
    UNION ALL SELECT 'Football', 'College football competition.'
    UNION ALL SELECT 'Volleyball', 'College volleyball competition.'
    UNION ALL SELECT 'Kabaddi', 'College kabaddi competition.'
    UNION ALL SELECT 'Badminton', 'College badminton competition.'
    UNION ALL SELECT 'Chess', 'College chess competition.'
    UNION ALL SELECT 'Basketball', 'College basketball competition.'
    UNION ALL SELECT 'Athletics', 'College athletics competition.'
) AS sample
WHERE @apply_sample_data = 1
  AND @sample_identity_conflict_count = 0
  AND NOT EXISTS (
      SELECT 1 FROM Sports existing WHERE existing.name = sample.name
  );

-- The 12 fictional student identifiers and reserved .invalid email addresses
-- are stable rerun keys. Exact existing pairs are preserved; partial identity
-- collisions stop the script before any inserts.
INSERT INTO Students (
    student_number, first_name, last_name, email, department_id,
    enrollment_status
)
SELECT sample.student_number, sample.first_name, sample.last_name,
       sample.email, @department_1, 'active'
FROM (
    SELECT 'P2-SAMPLE-001' AS student_number, 'Aanya' AS first_name, 'Sharma' AS last_name, 'p2.sample.001@example.invalid' AS email
    UNION ALL SELECT 'P2-SAMPLE-002', 'Rohan', 'Mehta', 'p2.sample.002@example.invalid'
    UNION ALL SELECT 'P2-SAMPLE-003', 'Ishita', 'Rao', 'p2.sample.003@example.invalid'
    UNION ALL SELECT 'P2-SAMPLE-004', 'Arjun', 'Nair', 'p2.sample.004@example.invalid'
    UNION ALL SELECT 'P2-SAMPLE-005', 'Kavya', 'Iyer', 'p2.sample.005@example.invalid'
    UNION ALL SELECT 'P2-SAMPLE-006', 'Vihaan', 'Kapoor', 'p2.sample.006@example.invalid'
    UNION ALL SELECT 'P2-SAMPLE-007', 'Sara', 'Khan', 'p2.sample.007@example.invalid'
    UNION ALL SELECT 'P2-SAMPLE-008', 'Dev', 'Patel', 'p2.sample.008@example.invalid'
    UNION ALL SELECT 'P2-SAMPLE-009', 'Meera', 'Joshi', 'p2.sample.009@example.invalid'
    UNION ALL SELECT 'P2-SAMPLE-010', 'Kabir', 'Singh', 'p2.sample.010@example.invalid'
    UNION ALL SELECT 'P2-SAMPLE-011', 'Ananya', 'Das', 'p2.sample.011@example.invalid'
    UNION ALL SELECT 'P2-SAMPLE-012', 'Neil', 'Thomas', 'p2.sample.012@example.invalid'
) AS sample
WHERE @apply_sample_data = 1
  AND @sample_identity_conflict_count = 0
  AND NOT EXISTS (
      SELECT 1
      FROM Students existing
      WHERE existing.student_number = sample.student_number
         OR existing.email = sample.email
  );

-- Each sample student has at most one player profile.
INSERT INTO Players (student_id, is_active)
SELECT s.student_id, TRUE
FROM Students s
WHERE @apply_sample_data = 1
  AND @sample_identity_conflict_count = 0
  AND s.student_number LIKE 'P2-SAMPLE-%'
  AND s.email = CONCAT(
      'p2.sample.',
      RIGHT(s.student_number, 3),
      '@example.invalid'
  )
  AND NOT EXISTS (
      SELECT 1 FROM Players existing WHERE existing.student_id = s.student_id
  );

-- Players 1-6 are eligible for cricket and chess; players 7-12 for football
-- and chess. Eligibility dates include the sample tournament dates.
INSERT INTO Player_Sports (player_id, sport_id, eligible_from, eligible_to)
SELECT p.player_id, sp.sport_id, DATE_SUB(CURRENT_DATE, INTERVAL 365 DAY), NULL
FROM (
    SELECT 'P2-SAMPLE-001' AS student_number, 'Cricket' AS sport_name
    UNION ALL SELECT 'P2-SAMPLE-002', 'Cricket'
    UNION ALL SELECT 'P2-SAMPLE-003', 'Cricket'
    UNION ALL SELECT 'P2-SAMPLE-004', 'Cricket'
    UNION ALL SELECT 'P2-SAMPLE-005', 'Cricket'
    UNION ALL SELECT 'P2-SAMPLE-006', 'Cricket'
    UNION ALL SELECT 'P2-SAMPLE-007', 'Football'
    UNION ALL SELECT 'P2-SAMPLE-008', 'Football'
    UNION ALL SELECT 'P2-SAMPLE-009', 'Football'
    UNION ALL SELECT 'P2-SAMPLE-010', 'Football'
    UNION ALL SELECT 'P2-SAMPLE-011', 'Football'
    UNION ALL SELECT 'P2-SAMPLE-012', 'Football'
    UNION ALL SELECT 'P2-SAMPLE-001', 'Chess'
    UNION ALL SELECT 'P2-SAMPLE-002', 'Chess'
    UNION ALL SELECT 'P2-SAMPLE-003', 'Chess'
    UNION ALL SELECT 'P2-SAMPLE-004', 'Chess'
    UNION ALL SELECT 'P2-SAMPLE-005', 'Chess'
    UNION ALL SELECT 'P2-SAMPLE-006', 'Chess'
    UNION ALL SELECT 'P2-SAMPLE-007', 'Chess'
    UNION ALL SELECT 'P2-SAMPLE-008', 'Chess'
    UNION ALL SELECT 'P2-SAMPLE-009', 'Chess'
    UNION ALL SELECT 'P2-SAMPLE-010', 'Chess'
    UNION ALL SELECT 'P2-SAMPLE-011', 'Chess'
    UNION ALL SELECT 'P2-SAMPLE-012', 'Chess'
) AS sample
JOIN Students s
  ON s.student_number = sample.student_number
 AND s.email = CONCAT(
      'p2.sample.',
      RIGHT(sample.student_number, 3),
      '@example.invalid'
 )
JOIN Players p ON p.student_id = s.student_id
JOIN Sports sp ON sp.name = sample.sport_name
WHERE @apply_sample_data = 1
  AND @sample_identity_conflict_count = 0
  AND NOT EXISTS (
      SELECT 1
      FROM Player_Sports existing
      WHERE existing.player_id = p.player_id
        AND existing.sport_id = sp.sport_id
  );

-- Department-based teams use discovered existing department IDs. If fewer
-- than four departments exist, rows requiring missing IDs are skipped.
INSERT INTO Teams (sport_id, department_id, name, team_code, is_active)
SELECT sp.sport_id, d.department_id, sample.team_name, sample.team_code, TRUE
FROM (
    SELECT 'Cricket' AS sport_name, 'P2 Sample Cricket A' AS team_name, 'P2-CA' AS team_code, 1 AS department_number
    UNION ALL SELECT 'Cricket', 'P2 Sample Cricket B', 'P2-CB', 2
    UNION ALL SELECT 'Football', 'P2 Sample Football A', 'P2-FA', 3
    UNION ALL SELECT 'Football', 'P2 Sample Football B', 'P2-FB', 4
) AS sample
JOIN Sports sp ON sp.name = sample.sport_name
JOIN Departments d
  ON d.department_id = CASE sample.department_number
      WHEN 1 THEN @department_1
      WHEN 2 THEN @department_2
      WHEN 3 THEN @department_3
      WHEN 4 THEN @department_4
  END
WHERE @apply_sample_data = 1
  AND @sample_identity_conflict_count = 0
  AND NOT EXISTS (
      SELECT 1
      FROM Teams existing
      WHERE existing.sport_id = sp.sport_id
        AND existing.department_id = d.department_id
        AND existing.name = sample.team_name
  );

-- Team roster assignments; every row is gated by a matching, date-valid
-- Player_Sports eligibility record for the team's sport.
INSERT INTO Team_Memberships (team_id, player_id, membership_from, membership_to)
SELECT team.team_id, p.player_id, '2026-01-01', NULL
FROM (
    SELECT 'P2 Sample Cricket A' AS team_name, 'P2-SAMPLE-001' AS student_number, 'Cricket' AS sport_name, 1 AS department_number
    UNION ALL SELECT 'P2 Sample Cricket A', 'P2-SAMPLE-002', 'Cricket', 1
    UNION ALL SELECT 'P2 Sample Cricket A', 'P2-SAMPLE-003', 'Cricket', 1
    UNION ALL SELECT 'P2 Sample Cricket B', 'P2-SAMPLE-004', 'Cricket', 2
    UNION ALL SELECT 'P2 Sample Cricket B', 'P2-SAMPLE-005', 'Cricket', 2
    UNION ALL SELECT 'P2 Sample Cricket B', 'P2-SAMPLE-006', 'Cricket', 2
    UNION ALL SELECT 'P2 Sample Football A', 'P2-SAMPLE-007', 'Football', 3
    UNION ALL SELECT 'P2 Sample Football A', 'P2-SAMPLE-008', 'Football', 3
    UNION ALL SELECT 'P2 Sample Football A', 'P2-SAMPLE-009', 'Football', 3
    UNION ALL SELECT 'P2 Sample Football B', 'P2-SAMPLE-010', 'Football', 4
    UNION ALL SELECT 'P2 Sample Football B', 'P2-SAMPLE-011', 'Football', 4
    UNION ALL SELECT 'P2 Sample Football B', 'P2-SAMPLE-012', 'Football', 4
) AS sample
JOIN Departments d
  ON d.department_id = CASE sample.department_number
      WHEN 1 THEN @department_1
      WHEN 2 THEN @department_2
      WHEN 3 THEN @department_3
      WHEN 4 THEN @department_4
  END
JOIN Teams team
  ON team.name = sample.team_name
 AND team.department_id = d.department_id
JOIN Sports sp ON sp.sport_id = team.sport_id AND sp.name = sample.sport_name
JOIN Students s
  ON s.student_number = sample.student_number
 AND s.email = CONCAT(
      'p2.sample.',
      RIGHT(sample.student_number, 3),
      '@example.invalid'
 )
JOIN Players p ON p.student_id = s.student_id
JOIN Player_Sports ps
  ON ps.player_id = p.player_id
 AND ps.sport_id = sp.sport_id
 AND ps.eligible_from <= CURRENT_DATE
 AND (ps.eligible_to IS NULL OR ps.eligible_to >= CURRENT_DATE)
WHERE @apply_sample_data = 1
  AND @sample_identity_conflict_count = 0
  AND NOT EXISTS (
      SELECT 1
      FROM Team_Memberships existing
      WHERE existing.team_id = team.team_id
        AND existing.player_id = p.player_id
        AND existing.membership_from = '2026-01-01'
  );

-- Names are explicitly sample-prefixed to avoid attaching fixtures or entries
-- to an unrelated tournament with a common title.
INSERT INTO Tournaments (
    sport_id, name, competition_format, season, start_date, end_date,
    status, is_published, description
)
SELECT sp.sport_id, sample.tournament_name, sample.competition_format,
       '2026', DATE_SUB(CURRENT_DATE, INTERVAL 5 DAY),
       DATE_ADD(CURRENT_DATE, INTERVAL 45 DAY), 'in_progress', TRUE,
       sample.description
FROM (
    SELECT 'Cricket' AS sport_name, 'Phase 2 Sample Cricket Cup 2026' AS tournament_name, 'team' AS competition_format, 'Fictional college cricket tournament sample.' AS description
    UNION ALL SELECT 'Football', 'Phase 2 Sample Football League 2026', 'team', 'Fictional college football tournament sample.'
    UNION ALL SELECT 'Chess', 'Phase 2 Sample Chess Open 2026', 'individual', 'Fictional college chess tournament sample.'
) AS sample
JOIN Sports sp ON sp.name = sample.sport_name
WHERE @apply_sample_data = 1
  AND @sample_identity_conflict_count = 0
  AND NOT EXISTS (
      SELECT 1
      FROM Tournaments existing
      WHERE existing.sport_id = sp.sport_id
        AND existing.name = sample.tournament_name
        AND existing.season = '2026'
  );

-- Scoring rules: standard win/draw/loss points for team competitions and
-- fractional draw points for the individual chess standings.
INSERT INTO Tournament_Scoring_Rules (
    tournament_id, points_for_win, points_for_draw, points_for_loss
)
SELECT t.tournament_id, sample.points_for_win, sample.points_for_draw,
       sample.points_for_loss
FROM (
    SELECT 'Phase 2 Sample Cricket Cup 2026' AS tournament_name, 3.00 AS points_for_win, 1.00 AS points_for_draw, 0.00 AS points_for_loss
    UNION ALL SELECT 'Phase 2 Sample Football League 2026', 3.00, 1.00, 0.00
    UNION ALL SELECT 'Phase 2 Sample Chess Open 2026', 1.00, 0.50, 0.00
) AS sample
JOIN Tournaments t ON t.name = sample.tournament_name AND t.season = '2026'
WHERE @apply_sample_data = 1
  AND @sample_identity_conflict_count = 0
  AND NOT EXISTS (
      SELECT 1
      FROM Tournament_Scoring_Rules existing
      WHERE existing.tournament_id = t.tournament_id
  );

-- Register two teams per team tournament and six players in the chess event.
INSERT INTO Tournament_Entries (tournament_id, team_id, player_id, status)
SELECT t.tournament_id, team.team_id, NULL, 'registered'
FROM (
    SELECT 'Phase 2 Sample Cricket Cup 2026' AS tournament_name, 'P2 Sample Cricket A' AS team_name, 1 AS department_number
    UNION ALL SELECT 'Phase 2 Sample Cricket Cup 2026', 'P2 Sample Cricket B', 2
    UNION ALL SELECT 'Phase 2 Sample Football League 2026', 'P2 Sample Football A', 3
    UNION ALL SELECT 'Phase 2 Sample Football League 2026', 'P2 Sample Football B', 4
) AS sample
JOIN Tournaments t ON t.name = sample.tournament_name AND t.season = '2026'
JOIN Departments d
  ON d.department_id = CASE sample.department_number
      WHEN 1 THEN @department_1
      WHEN 2 THEN @department_2
      WHEN 3 THEN @department_3
      WHEN 4 THEN @department_4
  END
JOIN Teams team
  ON team.name = sample.team_name
 AND team.department_id = d.department_id
 AND team.sport_id = t.sport_id
WHERE @apply_sample_data = 1
  AND @sample_identity_conflict_count = 0
  AND t.competition_format = 'team'
  AND NOT EXISTS (
      SELECT 1 FROM Tournament_Entries existing
      WHERE existing.tournament_id = t.tournament_id
        AND existing.team_id = team.team_id
  );

INSERT INTO Tournament_Entries (tournament_id, team_id, player_id, status)
SELECT t.tournament_id, NULL, p.player_id, 'registered'
FROM Tournaments t
JOIN Sports sp ON sp.sport_id = t.sport_id AND sp.name = 'Chess'
JOIN Students s
  ON s.student_number IN (
      'P2-SAMPLE-001', 'P2-SAMPLE-002', 'P2-SAMPLE-003',
      'P2-SAMPLE-004', 'P2-SAMPLE-005', 'P2-SAMPLE-006'
  )
 AND s.email = CONCAT(
      'p2.sample.',
      RIGHT(s.student_number, 3),
      '@example.invalid'
 )
JOIN Players p ON p.student_id = s.student_id
JOIN Player_Sports ps
  ON ps.player_id = p.player_id
 AND ps.sport_id = t.sport_id
 AND ps.eligible_from <= t.end_date
 AND (ps.eligible_to IS NULL OR ps.eligible_to >= t.start_date)
WHERE @apply_sample_data = 1
  AND @sample_identity_conflict_count = 0
  AND t.name = 'Phase 2 Sample Chess Open 2026'
  AND t.season = '2026'
  AND t.competition_format = 'individual'
  AND NOT EXISTS (
      SELECT 1 FROM Tournament_Entries existing
      WHERE existing.tournament_id = t.tournament_id
        AND existing.player_id = p.player_id
  );

-- Two completed and two upcoming matches per tournament.
INSERT INTO Matches (
    tournament_id, match_number, stage, round_name, scheduled_at, venue, status
)
SELECT t.tournament_id, sample.match_number, sample.stage, sample.round_name,
       sample.scheduled_at, sample.venue, sample.match_status
FROM (
    SELECT 'Phase 2 Sample Cricket Cup 2026' AS tournament_name, 1 AS match_number, 'Group' AS stage, 'Round 1' AS round_name, DATE_SUB(CURRENT_DATE, INTERVAL 2 DAY) AS scheduled_at, 'College Ground A' AS venue, 'completed' AS match_status
    UNION ALL SELECT 'Phase 2 Sample Cricket Cup 2026', 2, 'Group', 'Round 2', DATE_ADD(CURRENT_DATE, INTERVAL 3 DAY), 'College Ground A', 'scheduled'
    UNION ALL SELECT 'Phase 2 Sample Football League 2026', 1, 'League', 'Round 1', DATE_SUB(CURRENT_DATE, INTERVAL 1 DAY), 'College Stadium', 'completed'
    UNION ALL SELECT 'Phase 2 Sample Football League 2026', 2, 'League', 'Round 2', DATE_ADD(CURRENT_DATE, INTERVAL 4 DAY), 'College Stadium', 'scheduled'
    UNION ALL SELECT 'Phase 2 Sample Chess Open 2026', 1, 'Open', 'Round 1', DATE_SUB(CURRENT_DATE, INTERVAL 1 DAY), 'Library Hall', 'completed'
    UNION ALL SELECT 'Phase 2 Sample Chess Open 2026', 2, 'Open', 'Round 2', DATE_ADD(CURRENT_DATE, INTERVAL 2 DAY), 'Library Hall', 'scheduled'
) AS sample
JOIN Tournaments t ON t.name = sample.tournament_name AND t.season = '2026'
WHERE @apply_sample_data = 1
  AND @sample_identity_conflict_count = 0
  AND NOT EXISTS (
      SELECT 1 FROM Matches existing
      WHERE existing.tournament_id = t.tournament_id
        AND existing.match_number = sample.match_number
  );

-- Match participants are selected from entries in the same tournament.
INSERT INTO Match_Entries (match_id, entry_id)
SELECT m.match_id, te.entry_id
FROM (
    SELECT 'Phase 2 Sample Cricket Cup 2026' AS tournament_name, 1 AS match_number, 'team' AS participant_type, 'P2 Sample Cricket A' AS participant_key, 1 AS department_number
    UNION ALL SELECT 'Phase 2 Sample Cricket Cup 2026', 1, 'team', 'P2 Sample Cricket B', 2
    UNION ALL SELECT 'Phase 2 Sample Cricket Cup 2026', 2, 'team', 'P2 Sample Cricket A', 1
    UNION ALL SELECT 'Phase 2 Sample Cricket Cup 2026', 2, 'team', 'P2 Sample Cricket B', 2
    UNION ALL SELECT 'Phase 2 Sample Football League 2026', 1, 'team', 'P2 Sample Football A', 3
    UNION ALL SELECT 'Phase 2 Sample Football League 2026', 1, 'team', 'P2 Sample Football B', 4
    UNION ALL SELECT 'Phase 2 Sample Football League 2026', 2, 'team', 'P2 Sample Football A', 3
    UNION ALL SELECT 'Phase 2 Sample Football League 2026', 2, 'team', 'P2 Sample Football B', 4
    UNION ALL SELECT 'Phase 2 Sample Chess Open 2026', 1, 'player', 'P2-SAMPLE-001', NULL
    UNION ALL SELECT 'Phase 2 Sample Chess Open 2026', 1, 'player', 'P2-SAMPLE-002', NULL
    UNION ALL SELECT 'Phase 2 Sample Chess Open 2026', 1, 'player', 'P2-SAMPLE-003', NULL
    UNION ALL SELECT 'Phase 2 Sample Chess Open 2026', 1, 'player', 'P2-SAMPLE-004', NULL
    UNION ALL SELECT 'Phase 2 Sample Chess Open 2026', 2, 'player', 'P2-SAMPLE-005', NULL
    UNION ALL SELECT 'Phase 2 Sample Chess Open 2026', 2, 'player', 'P2-SAMPLE-006', NULL
) AS sample
JOIN Tournaments t ON t.name = sample.tournament_name AND t.season = '2026'
JOIN Matches m
  ON m.tournament_id = t.tournament_id
 AND m.match_number = sample.match_number
LEFT JOIN Teams team
  ON sample.participant_type = 'team'
 AND team.name = sample.participant_key
 AND team.sport_id = t.sport_id
 AND team.department_id = CASE sample.department_number
      WHEN 1 THEN @department_1
      WHEN 2 THEN @department_2
      WHEN 3 THEN @department_3
      WHEN 4 THEN @department_4
  END
LEFT JOIN Students s
  ON sample.participant_type = 'player'
 AND s.student_number = sample.participant_key
 AND s.email = CONCAT(
     'p2.sample.',
     RIGHT(sample.participant_key, 3),
     '@example.invalid'
 )
LEFT JOIN Players p ON p.student_id = s.student_id
JOIN Tournament_Entries te
  ON te.tournament_id = t.tournament_id
 AND (
      (sample.participant_type = 'team' AND te.team_id = team.team_id)
      OR (sample.participant_type = 'player' AND te.player_id = p.player_id)
 )
WHERE @apply_sample_data = 1
  AND @sample_identity_conflict_count = 0
  AND NOT EXISTS (
      SELECT 1 FROM Match_Entries existing
      WHERE existing.match_id = m.match_id AND existing.entry_id = te.entry_id
  );

-- Record numeric final scores only for completed matches and valid match
-- participants. Upcoming matches intentionally have no scores or results.
INSERT INTO Match_Scores (
    match_id, entry_id, segment_number, segment_label, numeric_value, text_value
)
SELECT m.match_id, me.entry_id, 1, sample.segment_label,
       sample.numeric_value, NULL
FROM (
    SELECT 'Phase 2 Sample Cricket Cup 2026' AS tournament_name, 1 AS match_number, 'team' AS participant_type, 'P2 Sample Cricket A' AS participant_key, 'Innings' AS segment_label, 156.000 AS numeric_value, 1 AS department_number
    UNION ALL SELECT 'Phase 2 Sample Cricket Cup 2026', 1, 'team', 'P2 Sample Cricket B', 'Innings', 149.000, 2
    UNION ALL SELECT 'Phase 2 Sample Football League 2026', 1, 'team', 'P2 Sample Football A', 'Final', 2.000, 3
    UNION ALL SELECT 'Phase 2 Sample Football League 2026', 1, 'team', 'P2 Sample Football B', 'Final', 2.000, 4
    UNION ALL SELECT 'Phase 2 Sample Chess Open 2026', 1, 'player', 'P2-SAMPLE-001', 'Points', 1.000, NULL
    UNION ALL SELECT 'Phase 2 Sample Chess Open 2026', 1, 'player', 'P2-SAMPLE-002', 'Points', 1.000, NULL
    UNION ALL SELECT 'Phase 2 Sample Chess Open 2026', 1, 'player', 'P2-SAMPLE-003', 'Points', 0.500, NULL
    UNION ALL SELECT 'Phase 2 Sample Chess Open 2026', 1, 'player', 'P2-SAMPLE-004', 'Points', 0.500, NULL
) AS sample
JOIN Tournaments t ON t.name = sample.tournament_name AND t.season = '2026'
JOIN Matches m
  ON m.tournament_id = t.tournament_id
 AND m.match_number = sample.match_number
 AND m.status = 'completed'
LEFT JOIN Teams team
  ON sample.participant_type = 'team'
 AND team.name = sample.participant_key
 AND team.sport_id = t.sport_id
 AND team.department_id = CASE sample.department_number
      WHEN 1 THEN @department_1
      WHEN 2 THEN @department_2
      WHEN 3 THEN @department_3
      WHEN 4 THEN @department_4
  END
LEFT JOIN Students s
  ON sample.participant_type = 'player'
 AND s.student_number = sample.participant_key
 AND s.email = CONCAT(
     'p2.sample.',
     RIGHT(sample.participant_key, 3),
     '@example.invalid'
 )
LEFT JOIN Players p ON p.student_id = s.student_id
JOIN Match_Entries me
  ON me.match_id = m.match_id
JOIN Tournament_Entries te
  ON te.tournament_id = t.tournament_id
 AND te.entry_id = me.entry_id
 AND (
      (sample.participant_type = 'team' AND te.team_id = team.team_id)
      OR (sample.participant_type = 'player' AND te.player_id = p.player_id)
 )
WHERE @apply_sample_data = 1
  AND @sample_identity_conflict_count = 0
  AND NOT EXISTS (
      SELECT 1 FROM Match_Scores existing
      WHERE existing.match_id = m.match_id
        AND existing.entry_id = me.entry_id
        AND existing.segment_number = 1
  );

-- Match_Results uses result_rank consistently with schema.sql. Matching names,
-- IDs, and tournament entries prevents results from attaching to unrelated
-- records. Equal result_rank values intentionally allow tied placements.
INSERT INTO Match_Results (
    match_id, entry_id, outcome, result_rank, official_note
)
SELECT m.match_id, me.entry_id, sample.outcome, sample.placement,
       'Fictional Phase 2 sample result.'
FROM (
    SELECT 'Phase 2 Sample Cricket Cup 2026' AS tournament_name, 1 AS match_number, 'team' AS participant_type, 'P2 Sample Cricket A' AS participant_key, 'win' AS outcome, NULL AS placement, 1 AS department_number
    UNION ALL SELECT 'Phase 2 Sample Cricket Cup 2026', 1, 'team', 'P2 Sample Cricket B', 'loss', NULL, 2
    UNION ALL SELECT 'Phase 2 Sample Football League 2026', 1, 'team', 'P2 Sample Football A', 'draw', NULL, 3
    UNION ALL SELECT 'Phase 2 Sample Football League 2026', 1, 'team', 'P2 Sample Football B', 'draw', NULL, 4
    UNION ALL SELECT 'Phase 2 Sample Chess Open 2026', 1, 'player', 'P2-SAMPLE-001', 'placed', 1, NULL
    UNION ALL SELECT 'Phase 2 Sample Chess Open 2026', 1, 'player', 'P2-SAMPLE-002', 'placed', 1, NULL
    UNION ALL SELECT 'Phase 2 Sample Chess Open 2026', 1, 'player', 'P2-SAMPLE-003', 'placed', 3, NULL
    UNION ALL SELECT 'Phase 2 Sample Chess Open 2026', 1, 'player', 'P2-SAMPLE-004', 'placed', 3, NULL
) AS sample
JOIN Tournaments t
  ON t.name = sample.tournament_name
 AND t.season = '2026'
JOIN Matches m
  ON m.tournament_id = t.tournament_id
 AND m.match_number = sample.match_number
 AND m.status = 'completed'
LEFT JOIN Teams team
  ON sample.participant_type = 'team'
 AND team.name = sample.participant_key
 AND team.sport_id = t.sport_id
 AND team.department_id = CASE sample.department_number
      WHEN 1 THEN @department_1
      WHEN 2 THEN @department_2
      WHEN 3 THEN @department_3
      WHEN 4 THEN @department_4
  END
LEFT JOIN Students s
  ON sample.participant_type = 'player'
 AND s.student_number = sample.participant_key
 AND s.email = CONCAT(
     'p2.sample.',
     RIGHT(sample.participant_key, 3),
     '@example.invalid'
 )
LEFT JOIN Players p ON p.student_id = s.student_id
JOIN Match_Entries me ON me.match_id = m.match_id
JOIN Tournament_Entries te
  ON te.tournament_id = t.tournament_id
 AND te.entry_id = me.entry_id
 AND (
      (sample.participant_type = 'team' AND te.team_id = team.team_id)
      OR (sample.participant_type = 'player' AND te.player_id = p.player_id)
 )
WHERE @apply_sample_data = 1
  AND @sample_identity_conflict_count = 0
  AND NOT EXISTS (
      SELECT 1
      FROM Match_Results existing
      WHERE existing.match_id = m.match_id
        AND existing.entry_id = me.entry_id
  );

COMMIT;

SELECT @apply_sample_data AS sample_data_applied,
       @department_1 AS sample_department_1,
       @department_2 AS sample_department_2,
       @department_3 AS sample_department_3,
       @department_4 AS sample_department_4;
