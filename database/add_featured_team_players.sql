USE sports_tournament_management;
SET NAMES utf8mb4;
START TRANSACTION;

INSERT IGNORE INTO Students (student_number,first_name,last_name,email,department_id,enrollment_status)
VALUES
('IPL-CSK-01','Ruturaj','Gaikwad','ruturaj.gaikwad@example.invalid',1,'active'),('IPL-CSK-02','MS','Dhoni','ms.dhoni@example.invalid',1,'active'),('IPL-CSK-03','Ravindra','Jadeja','ravindra.jadeja@example.invalid',1,'active'),('IPL-CSK-04','Shivam','Dube','shivam.dube@example.invalid',1,'active'),('IPL-CSK-05','Devon','Conway','devon.conway@example.invalid',1,'active'),('IPL-CSK-06','Rachin','Ravindra','rachin.ravindra@example.invalid',1,'active'),('IPL-CSK-07','Noor','Ahmad','noor.ahmad@example.invalid',1,'active'),('IPL-CSK-08','Deepak','Hooda','deepak.hooda@example.invalid',1,'active'),('IPL-CSK-09','Khaleel','Ahmed','khaleel.ahmed@example.invalid',1,'active'),('IPL-CSK-10','Shivam','Singh','shivam.singh@example.invalid',1,'active'),('IPL-CSK-11','Anshul','Kamboj','anshul.kamboj@example.invalid',1,'active'),
('IPL-MI-01','Rohit','Sharma','rohit.sharma@example.invalid',2,'active'),('IPL-MI-02','Suryakumar','Yadav','suryakumar.yadav@example.invalid',2,'active'),('IPL-MI-03','Hardik','Pandya','hardik.pandya@example.invalid',2,'active'),('IPL-MI-04','Tilak','Varma','tilak.varma@example.invalid',2,'active'),('IPL-MI-05','Jasprit','Bumrah','jasprit.bumrah@example.invalid',2,'active'),('IPL-MI-06','Ryan','Rickelton','ryan.rickelton@example.invalid',2,'active'),('IPL-MI-07','Ishan','Kishan','ishan.kishan@example.invalid',2,'active'),('IPL-MI-08','Naman','Dhir','naman.dhir@example.invalid',2,'active'),('IPL-MI-09','Nehal','Wadera','nehal.wadera@example.invalid',2,'active'),('IPL-MI-10','Trent','Boult','trent.boult@example.invalid',2,'active'),('IPL-MI-11','Mitchell','Santner','mitchell.santner@example.invalid',2,'active'),
('LIV-01','Mohamed','Salah','mohamed.salah@example.invalid',3,'active'),('LIV-02','Virgil','van Dijk','virgil.vandijk@example.invalid',3,'active'),('LIV-03','Alisson','Becker','alisson.becker@example.invalid',3,'active'),('LIV-04','Alexis','Mac Allister','alexis.macallister@example.invalid',3,'active'),('LIV-05','Dominik','Szoboszlai','dominik.szoboszlai@example.invalid',3,'active'),('LIV-06','Cody','Gakpo','cody.gakpo@example.invalid',3,'active'),('LIV-07','Ryan','Gravenberch','ryan.gravenberch@example.invalid',3,'active'),('LIV-08','Ibrahima','Konate','ibrahima.konate@example.invalid',3,'active'),('LIV-09','Andrew','Robertson','andrew.robertson@example.invalid',3,'active'),('LIV-10','Trent','Alexander-Arnold','trent.alexanderarnold@example.invalid',3,'active'),('LIV-11','Luis','Diaz','luis.diaz@example.invalid',3,'active'),
('BAR-01','Robert','Lewandowski','robert.lewandowski@example.invalid',4,'active'),('BAR-02','Lamine','Yamal','lamine.yamal@example.invalid',4,'active'),('BAR-03','Raphinha','Dias','raphinha.dias@example.invalid',4,'active'),('BAR-04','Pedri','Gonzalez','pedri.gonzalez@example.invalid',4,'active'),('BAR-05','Frenkie','de Jong','frenkie.dejong@example.invalid',4,'active'),('BAR-06','Marc-Andre','ter Stegen','marcandre.terstegen@example.invalid',4,'active'),('BAR-07','Jules','Kounde','jules.kounde@example.invalid',4,'active'),('BAR-08','Ronald','Araujo','ronald.araujo@example.invalid',4,'active'),('BAR-09','Alejandro','Balde','alejandro.balde@example.invalid',4,'active'),('BAR-10','Gavi','Paz','gavi.paz@example.invalid',4,'active'),('BAR-11','Ferran','Torres','ferran.torres@example.invalid',4,'active');

INSERT IGNORE INTO Players (student_id,is_active)
SELECT s.student_id,TRUE FROM Students s
WHERE s.student_number LIKE 'IPL-CSK-%' OR s.student_number LIKE 'IPL-MI-%'
   OR s.student_number LIKE 'LIV-%' OR s.student_number LIKE 'BAR-%';

INSERT IGNORE INTO Player_Sports (player_id,sport_id,eligible_from,eligible_to)
SELECT p.player_id,1,'2026-01-01',NULL
FROM Players p JOIN Students s ON s.student_id=p.student_id
WHERE s.student_number LIKE 'IPL-CSK-%' OR s.student_number LIKE 'IPL-MI-%';

INSERT IGNORE INTO Player_Sports (player_id,sport_id,eligible_from,eligible_to)
SELECT p.player_id,2,'2026-01-01',NULL
FROM Players p JOIN Students s ON s.student_id=p.student_id
WHERE s.student_number LIKE 'LIV-%' OR s.student_number LIKE 'BAR-%';

INSERT IGNORE INTO Teams (sport_id,department_id,name,team_code,is_active)
SELECT 1,1,'Chennai Super Kings','CSK',TRUE
WHERE NOT EXISTS (SELECT 1 FROM Teams WHERE sport_id=1 AND name='Chennai Super Kings');
INSERT IGNORE INTO Teams (sport_id,department_id,name,team_code,is_active)
SELECT 1,2,'Mumbai Indians','MI',TRUE
WHERE NOT EXISTS (SELECT 1 FROM Teams WHERE sport_id=1 AND name='Mumbai Indians');
INSERT IGNORE INTO Teams (sport_id,department_id,name,team_code,is_active)
SELECT 2,3,'Liverpool FC','LIV',TRUE
WHERE NOT EXISTS (SELECT 1 FROM Teams WHERE sport_id=2 AND name='Liverpool FC');
INSERT IGNORE INTO Teams (sport_id,department_id,name,team_code,is_active)
SELECT 2,4,'FC Barcelona','BAR',TRUE
WHERE NOT EXISTS (SELECT 1 FROM Teams WHERE sport_id=2 AND name='FC Barcelona');

INSERT IGNORE INTO Team_Memberships (team_id,player_id,membership_from,membership_to)
SELECT team.team_id,p.player_id,'2026-01-01',NULL
FROM Teams team JOIN Players p JOIN Students s ON p.student_id=s.student_id
WHERE (team.name='Chennai Super Kings' AND s.student_number LIKE 'IPL-CSK-%')
   OR (team.name='Mumbai Indians' AND s.student_number LIKE 'IPL-MI-%')
   OR (team.name='Liverpool FC' AND s.student_number LIKE 'LIV-%')
   OR (team.name='FC Barcelona' AND s.student_number LIKE 'BAR-%');

INSERT IGNORE INTO Tournament_Entries (tournament_id,team_id,player_id,status)
SELECT tournament_id,(SELECT team_id FROM Teams WHERE name='Chennai Super Kings'),NULL,'registered'
FROM Tournaments WHERE sport_id=1 AND name='Phase 2 Sample Cricket Cup 2026';
INSERT IGNORE INTO Tournament_Entries (tournament_id,team_id,player_id,status)
SELECT tournament_id,(SELECT team_id FROM Teams WHERE name='Mumbai Indians'),NULL,'registered'
FROM Tournaments WHERE sport_id=1 AND name='Phase 2 Sample Cricket Cup 2026';
INSERT IGNORE INTO Tournament_Entries (tournament_id,team_id,player_id,status)
SELECT tournament_id,(SELECT team_id FROM Teams WHERE name='Liverpool FC'),NULL,'registered'
FROM Tournaments WHERE sport_id=2 AND name='Phase 2 Sample Football League 2026';
INSERT IGNORE INTO Tournament_Entries (tournament_id,team_id,player_id,status)
SELECT tournament_id,(SELECT team_id FROM Teams WHERE name='FC Barcelona'),NULL,'registered'
FROM Tournaments WHERE sport_id=2 AND name='Phase 2 Sample Football League 2026';

INSERT IGNORE INTO Matches (tournament_id,match_number,stage,round_name,scheduled_at,venue,status)
SELECT tournament_id,
       COALESCE((SELECT MAX(match_number)+1 FROM Matches WHERE tournament_id=t.tournament_id),1),
       'Featured Match','Upcoming Fixture','2026-11-08 19:30:00','MA Chidambaram Stadium','scheduled'
FROM Tournaments t WHERE sport_id=1 AND name='Phase 2 Sample Cricket Cup 2026';

INSERT IGNORE INTO Matches (tournament_id,match_number,stage,round_name,scheduled_at,venue,status)
SELECT tournament_id,
       COALESCE((SELECT MAX(match_number)+1 FROM Matches WHERE tournament_id=t.tournament_id),1),
       'Featured Match','Upcoming Fixture','2026-11-09 20:00:00','Anfield Stadium','scheduled'
FROM Tournaments t WHERE sport_id=2 AND name='Phase 2 Sample Football League 2026';

INSERT IGNORE INTO Match_Entries (match_id,entry_id)
SELECT m.match_id,te.entry_id FROM Matches m
JOIN Tournament_Entries te ON te.tournament_id=m.tournament_id
JOIN Teams team ON team.team_id=te.team_id
WHERE team.name IN ('Chennai Super Kings','Mumbai Indians') AND m.status='scheduled';

INSERT IGNORE INTO Match_Entries (match_id,entry_id)
SELECT m.match_id,te.entry_id FROM Matches m
JOIN Tournament_Entries te ON te.tournament_id=m.tournament_id
JOIN Teams team ON team.team_id=te.team_id
WHERE team.name IN ('Liverpool FC','FC Barcelona') AND m.status='scheduled';

COMMIT;

SELECT team.name,COUNT(*) roster_size
FROM Teams team JOIN Team_Memberships tm ON tm.team_id=team.team_id
WHERE team.name IN ('Chennai Super Kings','Mumbai Indians','Liverpool FC','FC Barcelona')
GROUP BY team.team_id,team.name ORDER BY team.name;
