USE sports_tournament_management;
SET NAMES utf8mb4;
START TRANSACTION;

-- Create 12 new player students for each sport that previously had no demo team roster.
INSERT IGNORE INTO Students
    (student_number, first_name, last_name, email, department_id, enrollment_status)
WITH RECURSIVE nums AS (
    SELECT 1 AS n UNION ALL SELECT n + 1 FROM nums WHERE n < 72
),
names(pos, first_name, last_name) AS (
    SELECT 1,'Aarohi','Deshpande' UNION ALL SELECT 2,'Advik','Sawant' UNION ALL SELECT 3,'Amruta','Kulkarni'
    UNION ALL SELECT 4,'Ayush','Naik' UNION ALL SELECT 5,'Bhavya','Gokhale' UNION ALL SELECT 6,'Darsh','Patil'
    UNION ALL SELECT 7,'Devika','Phadke' UNION ALL SELECT 8,'Eshan','Jadhav' UNION ALL SELECT 9,'Gauri','Pawar'
    UNION ALL SELECT 10,'Harsha','Rane' UNION ALL SELECT 11,'Ishaan','Mahajan' UNION ALL SELECT 12,'Jhanvi','Joshi'
)
SELECT CONCAT('SPORT-PLAYER-', LPAD(n, 3, '0')),
       nm.first_name,
       nm.last_name,
       CONCAT('sport.player.', LPAD(n, 3, '0'), '@example.invalid'),
       ((n - 1) % 10) + 1,
       'active'
FROM nums
JOIN names nm ON nm.pos = MOD(n - 1, 12) + 1;

-- Create player profiles for the new students.
INSERT IGNORE INTO Players (student_id, is_active)
SELECT student_id, TRUE
FROM Students
WHERE student_number LIKE 'SPORT-PLAYER-%';

-- Assign every player to the requested sport (12 players in each of six sports).
INSERT IGNORE INTO Player_Sports (player_id, sport_id, eligible_from, eligible_to)
SELECT p.player_id, sp.sport_id, '2026-01-01', NULL
FROM Students s
JOIN Players p ON p.student_id = s.student_id
JOIN Sports sp
WHERE s.student_number LIKE 'SPORT-PLAYER-%'
  AND sp.name = CASE CEILING(CAST(SUBSTRING(s.student_number, 14) AS UNSIGNED) / 12)
      WHEN 1 THEN 'Athletics'
      WHEN 2 THEN 'Badminton'
      WHEN 3 THEN 'Basketball'
      WHEN 4 THEN 'Table Tennis'
      WHEN 5 THEN 'Tennis'
      WHEN 6 THEN 'Volleyball'
      ELSE 'Volleyball'
  END;

-- Add one active campus team for each sport.
INSERT IGNORE INTO Teams (sport_id, department_id, name, team_code, is_active)
SELECT sp.sport_id,
       d.department_id,
       CONCAT(d.department_name, ' ', sp.name, ' Squad'),
       CONCAT(UPPER(LEFT(REPLACE(sp.name, ' ', ''), 4)), '-', sp.sport_id),
       TRUE
FROM Sports sp
JOIN Departments d ON d.department_id = CASE sp.name
    WHEN 'Athletics' THEN 1 WHEN 'Badminton' THEN 2 WHEN 'Basketball' THEN 3
    WHEN 'Table Tennis' THEN 4 WHEN 'Tennis' THEN 5 WHEN 'Volleyball' THEN 6 END
WHERE sp.name IN ('Athletics','Badminton','Basketball','Table Tennis','Tennis','Volleyball');

-- Add eligible roster members: squads are capped at 12, or the standard smaller
-- volleyball/basketball side size where applicable.
INSERT IGNORE INTO Team_Memberships (team_id, player_id, membership_from, membership_to)
SELECT t.team_id, p.player_id, '2026-01-01', NULL
FROM Teams t
JOIN Sports sp ON sp.sport_id = t.sport_id
JOIN Students s ON s.student_number LIKE 'SPORT-PLAYER-%'
JOIN Players p ON p.student_id = s.student_id
JOIN Player_Sports ps ON ps.player_id = p.player_id AND ps.sport_id = sp.sport_id
WHERE sp.name IN ('Athletics','Badminton','Basketball','Table Tennis','Tennis','Volleyball')
  AND CAST(SUBSTRING(s.student_number, 14) AS UNSIGNED) BETWEEN
      CASE sp.name
          WHEN 'Athletics' THEN 1 WHEN 'Badminton' THEN 13 WHEN 'Basketball' THEN 25
          WHEN 'Table Tennis' THEN 37 WHEN 'Tennis' THEN 49 WHEN 'Volleyball' THEN 61 END
      AND CASE sp.name
          WHEN 'Athletics' THEN (CASE WHEN 12 <= 12 THEN 12 ELSE 12 END)
          WHEN 'Badminton' THEN 24 WHEN 'Basketball' THEN 36
          WHEN 'Table Tennis' THEN 48 WHEN 'Tennis' THEN 60 WHEN 'Volleyball' THEN 72 END
  AND NOT EXISTS (
      SELECT 1 FROM Team_Memberships tm WHERE tm.team_id = t.team_id AND tm.player_id = p.player_id
  );

-- Add a published team tournament for each sport so the data is available everywhere in the app.
INSERT IGNORE INTO Tournaments
    (sport_id, name, competition_format, season, start_date, end_date, status, is_published, description)
SELECT sp.sport_id, CONCAT('Campus ', sp.name, ' Championship 2026'), 'team', '2026',
       '2026-09-01', '2026-09-20', 'completed', TRUE,
       CONCAT('Demo ', sp.name, ' campus championship with complete player records.')
FROM Sports sp
WHERE sp.name IN ('Athletics','Badminton','Basketball','Table Tennis','Tennis','Volleyball');

INSERT IGNORE INTO Tournament_Scoring_Rules
    (tournament_id, points_for_win, points_for_draw, points_for_loss)
SELECT tournament_id, 3, 1, 0
FROM Tournaments
WHERE name LIKE 'Campus % Championship 2026'
  AND name IN (
      'Campus Athletics Championship 2026','Campus Badminton Championship 2026',
      'Campus Basketball Championship 2026','Campus Table Tennis Championship 2026',
      'Campus Tennis Championship 2026','Campus Volleyball Championship 2026'
  );

INSERT IGNORE INTO Tournament_Entries (tournament_id, team_id, player_id, status)
SELECT t.tournament_id, team.team_id, NULL, 'registered'
FROM Tournaments t
JOIN Teams team ON team.sport_id = t.sport_id
WHERE t.name IN (
      'Campus Athletics Championship 2026','Campus Badminton Championship 2026',
      'Campus Basketball Championship 2026','Campus Table Tennis Championship 2026',
      'Campus Tennis Championship 2026','Campus Volleyball Championship 2026'
);

COMMIT;

SELECT sp.name AS sport, COUNT(DISTINCT ps.player_id) AS players
FROM Sports sp
LEFT JOIN Player_Sports ps ON ps.sport_id = sp.sport_id
WHERE sp.name IN ('Athletics','Badminton','Basketball','Table Tennis','Tennis','Volleyball')
GROUP BY sp.sport_id, sp.name
ORDER BY sp.name;
