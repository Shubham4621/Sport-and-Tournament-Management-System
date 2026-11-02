USE sports_tournament_management;
SET NAMES utf8mb4;
SET SQL_SAFE_UPDATES = 0;

START TRANSACTION;

INSERT IGNORE INTO Sports (name, description, is_active) VALUES
    ('Tennis', 'Sample tennis sport.', TRUE),
    ('Table Tennis', 'Sample table tennis sport.', TRUE);

INSERT IGNORE INTO Admins (username, email, password_hash, display_name, is_active)
WITH RECURSIVE nums AS (
    SELECT 1 AS n
    UNION ALL SELECT n + 1 FROM nums WHERE n < 10
)
SELECT CONCAT('demo_admin_', LPAD(n, 2, '0')),
       CONCAT('demo.admin.', LPAD(n, 2, '0'), '@example.invalid'),
       'PLACEHOLDER-NOT-A-REAL-PASSWORD-HASH',
       CONCAT('Demo Administrator ', LPAD(n, 2, '0')),
       TRUE
FROM nums;

INSERT IGNORE INTO Departments (department_name, description)
WITH RECURSIVE nums AS (
    SELECT 1 AS n
    UNION ALL SELECT n + 1 FROM nums WHERE n < 10
)
SELECT CONCAT('Department of Computer Applications ', LPAD(n, 2, '0')),
       CONCAT('Sample academic department ', LPAD(n, 2, '0'))
FROM nums;

INSERT IGNORE INTO Students
    (student_number, first_name, last_name, email, department_id, enrollment_status)
WITH RECURSIVE nums AS (
    SELECT 1 AS n
    UNION ALL SELECT n + 1 FROM nums WHERE n < 90
),
deps AS (
    SELECT department_id, ROW_NUMBER() OVER (ORDER BY department_id) AS rn
    FROM Departments
    WHERE department_name LIKE 'Department of Computer Applications %'
)
SELECT CONCAT('DEMO-2026-', LPAD(n.n, 3, '0')),
       CONCAT('Player', LPAD(n.n, 3, '0')),
       CONCAT('Demo', CHAR(64 + (((n.n - 1) MOD 26) + 1))),
       CONCAT('demo.player.', LPAD(n.n, 3, '0'), '@example.invalid'),
       deps.department_id,
       'active'
FROM nums n
JOIN deps ON deps.rn = ((n.n - 1) MOD (SELECT COUNT(*) FROM deps)) + 1;

INSERT IGNORE INTO Players (student_id, is_active)
SELECT s.student_id, TRUE
FROM Students s
WHERE s.student_number LIKE 'DEMO-2026-%';

INSERT IGNORE INTO Player_Sports (player_id, sport_id, eligible_from, eligible_to)
SELECT p.player_id,
       CASE WHEN CAST(SUBSTRING(s.student_number, 11) AS UNSIGNED) <= 55 THEN cricket.sport_id ELSE kabaddi.sport_id END,
       '2026-01-01', NULL
FROM Players p
JOIN Students s ON s.student_id = p.student_id
JOIN Sports cricket ON cricket.name = 'Cricket'
JOIN Sports kabaddi ON kabaddi.name = 'Kabaddi'
WHERE s.student_number LIKE 'DEMO-2026-%';

INSERT IGNORE INTO Teams (sport_id, department_id, name, team_code, is_active)
WITH RECURSIVE nums AS (
    SELECT 1 AS n
    UNION ALL SELECT n + 1 FROM nums WHERE n < 10
)
SELECT CASE WHEN n <= 5 THEN cricket.sport_id ELSE kabaddi.sport_id END,
       dep.department_id,
       CASE WHEN n <= 5 THEN CONCAT('Campus Cricket Strikers ', LPAD(n, 2, '0'))
            ELSE CONCAT('Campus Kabaddi Raiders ', LPAD(n - 5, 2, '0')) END,
       CASE WHEN n <= 5 THEN CONCAT('CCS-', LPAD(n, 2, '0')) ELSE CONCAT('CKR-', LPAD(n - 5, 2, '0')) END,
       TRUE
FROM nums
JOIN Sports cricket ON cricket.name = 'Cricket'
JOIN Sports kabaddi ON kabaddi.name = 'Kabaddi'
JOIN Departments dep ON dep.department_name = CONCAT('Department of Computer Applications ', LPAD(n, 2, '0'));

INSERT IGNORE INTO Team_Memberships (team_id, player_id, membership_from, membership_to)
SELECT team.team_id, p.player_id, '2026-01-01', NULL
FROM Teams team
JOIN Sports sport ON sport.sport_id = team.sport_id
JOIN Students s ON s.student_number LIKE 'DEMO-2026-%'
JOIN Players p ON p.student_id = s.student_id
WHERE (sport.name = 'Cricket'
       AND team.team_code IS NOT NULL
       AND CAST(SUBSTRING(team.team_code, 5) AS UNSIGNED) = CEILING(CAST(SUBSTRING(s.student_number, 11) AS UNSIGNED) / 11)
       AND CAST(SUBSTRING(s.student_number, 11) AS UNSIGNED) BETWEEN 1 AND 55)
   OR (sport.name = 'Kabaddi'
       AND team.team_code IS NOT NULL
       AND CAST(SUBSTRING(team.team_code, 5) AS UNSIGNED) = CEILING((CAST(SUBSTRING(s.student_number, 11) AS SIGNED) - 55) / 7)
       AND CAST(SUBSTRING(s.student_number, 11) AS UNSIGNED) BETWEEN 56 AND 90);

INSERT IGNORE INTO Tournaments
    (sport_id, name, competition_format, season, start_date, end_date, status, is_published, description)
WITH RECURSIVE nums AS (
    SELECT 1 AS n
    UNION ALL SELECT n + 1 FROM nums WHERE n < 10
)
SELECT CASE WHEN MOD(n, 2) = 1 THEN cricket.sport_id ELSE kabaddi.sport_id END,
       CONCAT('Campus Championship ', LPAD(n, 2, '0'), ' - 2026'),
       'team',
       '2026',
       DATE_ADD('2026-08-01', INTERVAL (n - 1) DAY),
       DATE_ADD('2026-08-15', INTERVAL (n - 1) DAY),
       'completed',
       TRUE,
       CONCAT('Fictional completed campus tournament ', LPAD(n, 2, '0'))
FROM nums
JOIN Sports cricket ON cricket.name = 'Cricket'
JOIN Sports kabaddi ON kabaddi.name = 'Kabaddi';

INSERT IGNORE INTO Tournament_Scoring_Rules
    (tournament_id, points_for_win, points_for_draw, points_for_loss)
SELECT tournament_id, 3.00, 1.00, 0.00
FROM Tournaments
WHERE name LIKE 'Campus Championship %';

INSERT IGNORE INTO Tournament_Entries (tournament_id, team_id, player_id, status)
SELECT t.tournament_id, team.team_id, NULL, 'registered'
FROM Tournaments t
JOIN Teams team ON team.sport_id = t.sport_id
WHERE t.name LIKE 'Campus Championship %' AND team.is_active = TRUE;

INSERT IGNORE INTO Matches
    (tournament_id, match_number, stage, round_name, scheduled_at, venue, status)
SELECT tournament_id, 1, 'Final', 'Championship Final',
       DATE_ADD(end_date, INTERVAL 12 HOUR), 'Main Campus Arena', 'completed'
FROM Tournaments
WHERE name LIKE 'Campus Championship %';

INSERT IGNORE INTO Match_Entries (match_id, entry_id)
SELECT ranked.match_id, te.entry_id
FROM (
    SELECT m.match_id, m.tournament_id,
           ROW_NUMBER() OVER (PARTITION BY m.tournament_id ORDER BY te.entry_id) AS rn,
           te.entry_id
    FROM Matches m
    JOIN Tournament_Entries te ON te.tournament_id = m.tournament_id
    WHERE m.match_number = 1
      AND te.team_id IS NOT NULL
      AND te.status = 'registered'
) ranked
JOIN Tournament_Entries te ON te.entry_id = ranked.entry_id
JOIN Matches m ON m.match_id = ranked.match_id
WHERE ranked.rn <= 2
  AND NOT EXISTS (
      SELECT 1 FROM Match_Entries existing
      WHERE existing.match_id = ranked.match_id AND existing.entry_id = ranked.entry_id
  );

INSERT IGNORE INTO Match_Scores (match_id, entry_id, segment_number, numeric_value, text_value)
SELECT me.match_id, me.entry_id, 1,
       CASE WHEN ROW_NUMBER() OVER (PARTITION BY me.match_id ORDER BY me.entry_id) = 1 THEN 2.0 ELSE 1.0 END,
       NULL
FROM Match_Entries me
JOIN Matches m ON m.match_id = me.match_id
JOIN Tournaments t ON t.tournament_id = m.tournament_id
WHERE t.name LIKE 'Campus Championship %';

INSERT IGNORE INTO Match_Results
    (match_id, entry_id, outcome, result_rank, official_note)
SELECT me.match_id, me.entry_id,
       CASE WHEN ROW_NUMBER() OVER (PARTITION BY me.match_id ORDER BY me.entry_id) = 1 THEN 'win' ELSE 'loss' END,
       CASE WHEN ROW_NUMBER() OVER (PARTITION BY me.match_id ORDER BY me.entry_id) = 1 THEN 1 ELSE 2 END,
       'Demo match result recorded by database population script.'
FROM Match_Entries me
JOIN Matches m ON m.match_id = me.match_id
JOIN Tournaments t ON t.tournament_id = m.tournament_id
WHERE t.name LIKE 'Campus Championship %';

COMMIT;
SET SQL_SAFE_UPDATES = 1;

SELECT table_name, row_count
FROM (
    SELECT 'Admins' table_name, COUNT(*) row_count FROM Admins
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
) counts
ORDER BY table_name;
