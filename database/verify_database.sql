-- Read-only verification for MySQL 8.0+
-- Run with the sports_tournament_management database selected.
USE sports_tournament_management;

-- 1. Confirm required tables are present and report any missing names.
WITH expected_tables AS (
    SELECT 'Admins' AS table_name UNION ALL
    SELECT 'Sports' UNION ALL
    SELECT 'Departments' UNION ALL
    SELECT 'Students' UNION ALL
    SELECT 'Players' UNION ALL
    SELECT 'Player_Sports' UNION ALL
    SELECT 'Teams' UNION ALL
    SELECT 'Team_Memberships' UNION ALL
    SELECT 'Tournaments' UNION ALL
    SELECT 'Tournament_Scoring_Rules' UNION ALL
    SELECT 'Tournament_Entries' UNION ALL
    SELECT 'Matches' UNION ALL
    SELECT 'Match_Entries' UNION ALL
    SELECT 'Match_Scores' UNION ALL
    SELECT 'Match_Results'
)
SELECT e.table_name,
       CASE WHEN t.table_name IS NULL THEN 'MISSING' ELSE 'PRESENT' END AS table_status
FROM expected_tables e
LEFT JOIN information_schema.tables t
    ON t.table_schema = DATABASE()
   AND t.table_name = e.table_name
ORDER BY e.table_name;

-- 2. Total row counts for all expected tables.
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

-- 3. Column types, nullability, defaults, and auto-increment attributes.
SELECT table_name, ordinal_position, column_name, column_type, is_nullable,
       column_default, extra
FROM information_schema.columns
WHERE table_schema = DATABASE()
ORDER BY table_name, ordinal_position;

-- 4. Table engines and character sets/collations.
SELECT table_name, engine, table_collation
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- 5. Primary keys, unique constraints, and foreign-key definitions.
SELECT tc.table_name, tc.constraint_name, tc.constraint_type,
       kcu.column_name, kcu.referenced_table_name,
       kcu.referenced_column_name, kcu.ordinal_position
FROM information_schema.table_constraints tc
LEFT JOIN information_schema.key_column_usage kcu
    ON kcu.constraint_schema = tc.constraint_schema
   AND kcu.table_name = tc.table_name
   AND kcu.constraint_name = tc.constraint_name
WHERE tc.constraint_schema = DATABASE()
  AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE', 'FOREIGN KEY')
ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name,
         kcu.ordinal_position;

-- 6. CHECK constraints, including their enforced state.
SELECT tc.table_name, tc.constraint_name, cc.check_clause,
       tc.enforced
FROM information_schema.table_constraints tc
JOIN information_schema.check_constraints cc
    ON cc.constraint_schema = tc.constraint_schema
   AND cc.constraint_name = tc.constraint_name
WHERE tc.constraint_schema = DATABASE()
  AND tc.constraint_type = 'CHECK'
ORDER BY tc.table_name, tc.constraint_name;

-- 7. Indexes and their column ordering/uniqueness.
SELECT table_name, index_name, non_unique, seq_in_index, column_name,
       index_type
FROM information_schema.statistics
WHERE table_schema = DATABASE()
ORDER BY table_name, index_name, seq_in_index;

-- Tied ranks must remain possible; this query should return no rows.
SELECT index_name
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name = 'Match_Results'
  AND non_unique = 0
GROUP BY index_name
HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')
       = 'match_id,result_rank';

-- 8. Check the required result_rank column and flag a legacy rank column.
SELECT
    SUM(column_name = 'result_rank') > 0 AS result_rank_present,
    SUM(column_name = 'rank') > 0 AS legacy_rank_present
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'Match_Results'
  AND column_name IN ('rank', 'result_rank');

-- 9. Department directory and student affiliations.
SELECT department_id, department_name
FROM Departments
ORDER BY department_name;

SELECT s.student_id, s.student_number, s.first_name, s.last_name,
       s.email, d.department_name, s.enrollment_status
FROM Students s
LEFT JOIN Departments d ON d.department_id = s.department_id
ORDER BY s.student_number;

-- 10. Players and their sport eligibility.
SELECT p.player_id, s.student_number, s.first_name, s.last_name,
       sp.name AS sport_name, ps.eligible_from, ps.eligible_to,
       p.is_active
FROM Players p
JOIN Students s ON s.student_id = p.student_id
LEFT JOIN Player_Sports ps ON ps.player_id = p.player_id
LEFT JOIN Sports sp ON sp.sport_id = ps.sport_id
ORDER BY s.student_number, sp.name;

-- 11. Teams and dated roster memberships.
SELECT t.team_id, t.name AS team_name, sp.name AS sport_name,
       d.department_name, s.student_number, s.first_name, s.last_name,
       tm.membership_from, tm.membership_to
FROM Teams t
JOIN Sports sp ON sp.sport_id = t.sport_id
JOIN Departments d ON d.department_id = t.department_id
LEFT JOIN Team_Memberships tm ON tm.team_id = t.team_id
LEFT JOIN Players p ON p.player_id = tm.player_id
LEFT JOIN Students s ON s.student_id = p.student_id
ORDER BY sp.name, d.department_name, t.name, s.student_number;

-- 12. Tournaments with entries (team or individual).
SELECT t.tournament_id, t.name AS tournament_name, sp.name AS sport_name,
       t.competition_format, t.season, t.status, t.is_published,
       te.entry_id, te.status AS entry_status,
       COALESCE(team.name, CONCAT(st.first_name, ' ', st.last_name)) AS participant
FROM Tournaments t
JOIN Sports sp ON sp.sport_id = t.sport_id
LEFT JOIN Tournament_Entries te ON te.tournament_id = t.tournament_id
LEFT JOIN Teams team ON team.team_id = te.team_id
LEFT JOIN Players p ON p.player_id = te.player_id
LEFT JOIN Students st ON st.student_id = p.student_id
ORDER BY t.start_date, t.name, te.entry_id;

-- 13. Matches, participants, segment scores, and declared outcomes.
SELECT t.name AS tournament_name, m.match_id, m.match_number,
       m.stage, m.scheduled_at, m.status AS match_status,
       te.entry_id,
       COALESCE(team.name, CONCAT(st.first_name, ' ', st.last_name)) AS participant,
       me_score.segment_number, me_score.segment_label,
       me_score.numeric_value, me_score.text_value,
       mr.*
FROM Matches m
JOIN Tournaments t ON t.tournament_id = m.tournament_id
LEFT JOIN Match_Entries me ON me.match_id = m.match_id
LEFT JOIN Tournament_Entries te ON te.entry_id = me.entry_id
LEFT JOIN Teams team ON team.team_id = te.team_id
LEFT JOIN Players p ON p.player_id = te.player_id
LEFT JOIN Students st ON st.student_id = p.student_id
LEFT JOIN Match_Scores me_score
    ON me_score.match_id = me.match_id
   AND me_score.entry_id = me.entry_id
LEFT JOIN Match_Results mr
    ON mr.match_id = me.match_id
   AND mr.entry_id = me.entry_id
ORDER BY t.name, m.match_number, te.entry_id, me_score.segment_number;

-- 14. Expected to return no rows: cross-table integrity exceptions.
-- These checks supplement, rather than replace, the enforced foreign keys.
SELECT 'team_entry_wrong_format_or_sport' AS issue, te.entry_id AS row_id
FROM Tournament_Entries te
JOIN Tournaments t ON t.tournament_id = te.tournament_id
LEFT JOIN Teams team ON team.team_id = te.team_id
LEFT JOIN Players p ON p.player_id = te.player_id
LEFT JOIN Player_Sports ps
    ON ps.player_id = p.player_id
   AND ps.sport_id = t.sport_id
   AND ps.eligible_from <= t.end_date
   AND (ps.eligible_to IS NULL OR ps.eligible_to >= t.start_date)
WHERE (te.team_id IS NOT NULL
       AND (t.competition_format <> 'team' OR team.sport_id <> t.sport_id))
   OR (te.player_id IS NOT NULL
       AND (t.competition_format <> 'individual' OR ps.player_id IS NULL))
UNION ALL
SELECT 'entry_participant_xor_violation', te.entry_id
FROM Tournament_Entries te
WHERE (te.team_id IS NULL AND te.player_id IS NULL)
   OR (te.team_id IS NOT NULL AND te.player_id IS NOT NULL)
UNION ALL
SELECT 'match_entry_wrong_tournament', me.match_id
FROM Match_Entries me
JOIN Matches m ON m.match_id = me.match_id
JOIN Tournament_Entries te ON te.entry_id = me.entry_id
WHERE m.tournament_id <> te.tournament_id
UNION ALL
SELECT 'team_member_not_eligible_for_team_sport', tm.team_id
FROM Team_Memberships tm
JOIN Teams team ON team.team_id = tm.team_id
LEFT JOIN Player_Sports ps
    ON ps.player_id = tm.player_id
   AND ps.sport_id = team.sport_id
   AND ps.eligible_from <= COALESCE(tm.membership_to, CURRENT_DATE)
   AND (ps.eligible_to IS NULL OR ps.eligible_to >= tm.membership_from)
WHERE ps.player_id IS NULL;

-- Overlapping memberships in the same sport are also prohibited by the design.
SELECT tm1.player_id AS player_id, team1.sport_id AS sport_id,
       tm1.team_id AS first_team_id, tm2.team_id AS second_team_id
FROM Team_Memberships tm1
JOIN Team_Memberships tm2
  ON tm2.player_id = tm1.player_id
 AND tm2.team_id > tm1.team_id
 AND tm1.membership_from <= COALESCE(tm2.membership_to, '9999-12-31')
 AND tm2.membership_from <= COALESCE(tm1.membership_to, '9999-12-31')
JOIN Teams team1 ON team1.team_id = tm1.team_id
JOIN Teams team2
  ON team2.team_id = tm2.team_id
 AND team2.sport_id = team1.sport_id
ORDER BY tm1.player_id, team1.sport_id;

-- 15. Foreign-key orphans should be impossible with enabled constraints;
-- this aggregate reports any rows if constraints were disabled or bypassed.
SELECT 'students_without_department_parent' AS check_name, COUNT(*) AS violations
FROM Students s LEFT JOIN Departments d ON d.department_id = s.department_id
WHERE s.department_id IS NOT NULL AND d.department_id IS NULL
UNION ALL
SELECT 'players_without_student_parent', COUNT(*)
FROM Players p LEFT JOIN Students s ON s.student_id = p.student_id
WHERE s.student_id IS NULL
UNION ALL
SELECT 'player_sports_without_player_parent', COUNT(*)
FROM Player_Sports ps LEFT JOIN Players p ON p.player_id = ps.player_id
WHERE p.player_id IS NULL
UNION ALL
SELECT 'player_sports_without_sport_parent', COUNT(*)
FROM Player_Sports ps LEFT JOIN Sports sp ON sp.sport_id = ps.sport_id
WHERE sp.sport_id IS NULL
UNION ALL
SELECT 'teams_without_sport_parent', COUNT(*)
FROM Teams team LEFT JOIN Sports sp ON sp.sport_id = team.sport_id
WHERE sp.sport_id IS NULL
UNION ALL
SELECT 'teams_without_department_parent', COUNT(*)
FROM Teams team LEFT JOIN Departments d ON d.department_id = team.department_id
WHERE d.department_id IS NULL
UNION ALL
SELECT 'team_memberships_without_team_parent', COUNT(*)
FROM Team_Memberships tm LEFT JOIN Teams team ON team.team_id = tm.team_id
WHERE team.team_id IS NULL
UNION ALL
SELECT 'team_memberships_without_player_parent', COUNT(*)
FROM Team_Memberships tm LEFT JOIN Players p ON p.player_id = tm.player_id
WHERE p.player_id IS NULL
UNION ALL
SELECT 'tournaments_without_sport_parent', COUNT(*)
FROM Tournaments t LEFT JOIN Sports sp ON sp.sport_id = t.sport_id
WHERE sp.sport_id IS NULL
UNION ALL
SELECT 'scoring_rules_without_tournament_parent', COUNT(*)
FROM Tournament_Scoring_Rules rules
LEFT JOIN Tournaments t ON t.tournament_id = rules.tournament_id
WHERE t.tournament_id IS NULL
UNION ALL
SELECT 'entries_without_tournament_parent', COUNT(*)
FROM Tournament_Entries te
LEFT JOIN Tournaments t ON t.tournament_id = te.tournament_id
WHERE t.tournament_id IS NULL
UNION ALL
SELECT 'entries_without_team_parent', COUNT(*)
FROM Tournament_Entries te LEFT JOIN Teams team ON team.team_id = te.team_id
WHERE te.team_id IS NOT NULL AND team.team_id IS NULL
UNION ALL
SELECT 'entries_without_player_parent', COUNT(*)
FROM Tournament_Entries te LEFT JOIN Players p ON p.player_id = te.player_id
WHERE te.player_id IS NOT NULL AND p.player_id IS NULL
UNION ALL
SELECT 'matches_without_tournament_parent', COUNT(*)
FROM Matches m LEFT JOIN Tournaments t ON t.tournament_id = m.tournament_id
WHERE t.tournament_id IS NULL
UNION ALL
SELECT 'match_entries_without_match_parent', COUNT(*)
FROM Match_Entries me LEFT JOIN Matches m ON m.match_id = me.match_id
WHERE m.match_id IS NULL
UNION ALL
SELECT 'match_entries_without_tournament_entry_parent', COUNT(*)
FROM Match_Entries me
LEFT JOIN Tournament_Entries te ON te.entry_id = me.entry_id
WHERE te.entry_id IS NULL
UNION ALL
SELECT 'scores_without_match_entry_parent', COUNT(*)
FROM Match_Scores score
LEFT JOIN Match_Entries me
  ON me.match_id = score.match_id AND me.entry_id = score.entry_id
WHERE me.match_id IS NULL
UNION ALL
SELECT 'results_without_match_entry_parent', COUNT(*)
FROM Match_Results result_row
LEFT JOIN Match_Entries me
  ON me.match_id = result_row.match_id AND me.entry_id = result_row.entry_id
WHERE me.match_id IS NULL;
