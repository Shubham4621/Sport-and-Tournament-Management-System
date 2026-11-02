USE sports_tournament_management;

UPDATE Students s
JOIN Players p ON p.student_id = s.student_id
JOIN Player_Sports ps ON ps.player_id = p.player_id
JOIN Sports sp ON sp.sport_id = ps.sport_id
SET s.first_name = ELT((CAST(SUBSTRING(s.student_number, 14) AS UNSIGNED) - 1) % 24 + 1,
    'Aarohi','Advik','Amruta','Ayush','Bhavya','Darsh','Devika','Eshan','Gauri','Harsha','Ishaan','Jhanvi',
    'Kartik','Lavanya','Madhav','Naina','Omkar','Prisha','Raghav','Sanika','Tanmay','Urvi','Vihan','Yashita'),
    s.last_name = CONCAT(ELT((CAST(SUBSTRING(s.student_number, 14) AS UNSIGNED) - 1) % 24 + 1,
    'Deshpande','Sawant','Kulkarni','Naik','Gokhale','Patil','Phadke','Jadhav','Pawar','Rane','Mahajan','Joshi',
    'Bokil','Khanna','More','Suryavanshi','Chitale','Kapoor','Thackeray','Soman','Kothari','Desai','Pandit','Mantri'),
    ' ', LPAD(CAST(SUBSTRING(s.student_number, 14) AS UNSIGNED), 2, '0'))
WHERE s.student_number LIKE 'SPORT-PLAYER-%';

-- Ensure each sport player participates in only their assigned sport.
DELETE ps
FROM Player_Sports ps
JOIN Players p ON p.player_id = ps.player_id
JOIN Students s ON s.student_id = p.student_id
WHERE s.student_number LIKE 'SPORT-PLAYER-%'
  AND ps.sport_id NOT IN (
      SELECT sport_id FROM (
          SELECT sp.sport_id, sp.name
          FROM Sports sp
          WHERE sp.name = CASE CEILING(CAST(SUBSTRING(s.student_number, 14) AS UNSIGNED) / 12)
              WHEN 1 THEN 'Athletics'
              WHEN 2 THEN 'Badminton'
              WHEN 3 THEN 'Basketball'
              WHEN 4 THEN 'Table Tennis'
              WHEN 5 THEN 'Tennis'
              WHEN 6 THEN 'Volleyball'
          END
      ) assigned_sport
  );

SELECT sp.name AS sport,
       COUNT(DISTINCT ps.player_id) AS players,
       COUNT(DISTINCT CONCAT(s.first_name, ' ', s.last_name)) AS distinct_names
FROM Sports sp
JOIN Player_Sports ps ON ps.sport_id = sp.sport_id
JOIN Players p ON p.player_id = ps.player_id
JOIN Students s ON s.student_id = p.student_id
WHERE sp.name IN ('Athletics','Badminton','Basketball','Table Tennis','Tennis','Volleyball')
GROUP BY sp.sport_id, sp.name
ORDER BY sp.name;

SELECT MAX(sport_count) AS maximum_sports_per_player
FROM (
    SELECT p.player_id, COUNT(*) AS sport_count
    FROM Players p JOIN Player_Sports ps ON ps.player_id = p.player_id
    GROUP BY p.player_id
) counts;
