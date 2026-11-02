USE sports_tournament_management;
SET NAMES utf8mb4;
START TRANSACTION;

-- Add useful descriptions for every sport shown by the website.
UPDATE Sports SET description = CASE name
    WHEN 'Cricket' THEN 'Bat-and-ball team sport played with eleven players per side.'
    WHEN 'Football' THEN 'Association football played by two teams of eleven players.'
    WHEN 'Volleyball' THEN 'Indoor or beach team sport played over a net.'
    WHEN 'Kabaddi' THEN 'Fast-paced contact team sport played with seven players per side.'
    WHEN 'Badminton' THEN 'Racket sport played in singles or doubles formats.'
    WHEN 'Chess' THEN 'Strategic board sport played between individual competitors.'
    WHEN 'Basketball' THEN 'Court team sport where teams score by shooting into a hoop.'
    WHEN 'Athletics' THEN 'Track and field events covering running, jumping, and throwing.'
    WHEN 'Tennis' THEN 'Singles or doubles racket sport played on a marked court.'
    WHEN 'Table Tennis' THEN 'Fast indoor racket sport played across a divided table.'
END
WHERE name IN ('Cricket','Football','Volleyball','Kabaddi','Badminton','Chess','Basketball','Athletics','Tennis','Table Tennis');

-- Replace generated-looking demonstration names with realistic sample names.
UPDATE Students
SET first_name = CASE MOD(CAST(SUBSTRING(student_number, 11) AS UNSIGNED), 20)
        WHEN 0 THEN 'Aarav' WHEN 1 THEN 'Vivaan' WHEN 2 THEN 'Aditya' WHEN 3 THEN 'Vihaan'
        WHEN 4 THEN 'Arjun' WHEN 5 THEN 'Krishna' WHEN 6 THEN 'Sai' WHEN 7 THEN 'Kabir'
        WHEN 8 THEN 'Ananya' WHEN 9 THEN 'Diya' WHEN 10 THEN 'Isha' WHEN 11 THEN 'Aditi'
        WHEN 12 THEN 'Priya' WHEN 13 THEN 'Meera' WHEN 14 THEN 'Nisha' WHEN 15 THEN 'Riya'
        WHEN 16 THEN 'Saanvi' WHEN 17 THEN 'Kavya' WHEN 18 THEN 'Neha' ELSE 'Tanvi'
    END,
    last_name = CASE MOD(CAST(SUBSTRING(student_number, 11) AS UNSIGNED), 20)
        WHEN 0 THEN 'Patel' WHEN 1 THEN 'Sharma' WHEN 2 THEN 'Deshmukh' WHEN 3 THEN 'Joshi'
        WHEN 4 THEN 'Kulkarni' WHEN 5 THEN 'Mehta' WHEN 6 THEN 'Nair' WHEN 7 THEN 'Iyer'
        WHEN 8 THEN 'Rao' WHEN 9 THEN 'Singh' WHEN 10 THEN 'Gupta' WHEN 11 THEN 'Verma'
        WHEN 12 THEN 'Reddy' WHEN 13 THEN 'Jadhav' WHEN 14 THEN 'Kadam' WHEN 15 THEN 'Mishra'
        WHEN 16 THEN 'Naik' WHEN 17 THEN 'Chavan' WHEN 18 THEN 'Shinde' ELSE 'Pandey'
    END
WHERE student_number LIKE 'DEMO-2026-%';

-- Realistic non-player students. These deliberately have no Players row.
INSERT IGNORE INTO Students
    (student_number, first_name, last_name, email, department_id, enrollment_status)
VALUES
('NONPLAYER-001','Om','Bhosale','nonplayer.001@example.invalid',1,'active'),
('NONPLAYER-002','Mira','Sawant','nonplayer.002@example.invalid',2,'active'),
('NONPLAYER-003','Dev','Kale','nonplayer.003@example.invalid',3,'active'),
('NONPLAYER-004','Parth','Pawar','nonplayer.004@example.invalid',4,'inactive'),
('NONPLAYER-005','Tara','Wagh','nonplayer.005@example.invalid',5,'active'),
('NONPLAYER-006','Rohan','More','nonplayer.006@example.invalid',6,'active'),
('NONPLAYER-007','Avni','Salunkhe','nonplayer.007@example.invalid',7,'graduated'),
('NONPLAYER-008','Yash','Phadke','nonplayer.008@example.invalid',8,'active'),
('NONPLAYER-009','Ira','Bendre','nonplayer.009@example.invalid',9,'active'),
('NONPLAYER-010','Atharv','Dixit','nonplayer.010@example.invalid',10,'active'),
('NONPLAYER-011','Zara','Mhatre','nonplayer.011@example.invalid',1,'active'),
('NONPLAYER-012','Nikhil','Gavade','nonplayer.012@example.invalid',2,'inactive'),
('NONPLAYER-013','Anaya','Thakur','nonplayer.013@example.invalid',3,'active'),
('NONPLAYER-014','Reyansh','Inamdar','nonplayer.014@example.invalid',4,'active'),
('NONPLAYER-015','Myra','Sonavane','nonplayer.015@example.invalid',5,'active'),
('NONPLAYER-016','Harsh','Gaikwad','nonplayer.016@example.invalid',6,'graduated'),
('NONPLAYER-017','Siya','Sable','nonplayer.017@example.invalid',7,'active'),
('NONPLAYER-018','Vedant','Pakhale','nonplayer.018@example.invalid',8,'active'),
('NONPLAYER-019','Kiara','Kamble','nonplayer.019@example.invalid',9,'active'),
('NONPLAYER-020','Samarth','Mahajan','nonplayer.020@example.invalid',10,'active'),
('NONPLAYER-021','Navya','Ambekar','nonplayer.021@example.invalid',1,'active'),
('NONPLAYER-022','Pranav','Londhe','nonplayer.022@example.invalid',2,'inactive'),
('NONPLAYER-023','Aisha','Bhosale','nonplayer.023@example.invalid',3,'active'),
('NONPLAYER-024','Dhruv','Yadav','nonplayer.024@example.invalid',4,'active'),
('NONPLAYER-025','Vanya','Hire','nonplayer.025@example.invalid',5,'active'),
('NONPLAYER-026','Neil','Kulkarni','nonplayer.026@example.invalid',6,'graduated'),
('NONPLAYER-027','Rhea','Gokhale','nonplayer.027@example.invalid',7,'active'),
('NONPLAYER-028','Ayaan','Sathe','nonplayer.028@example.invalid',8,'active'),
('NONPLAYER-029','Tanishka','Apte','nonplayer.029@example.invalid',9,'active'),
('NONPLAYER-030','Mihir','Bhatt','nonplayer.030@example.invalid',10,'active');

COMMIT;

SELECT 'Sports' AS table_name, COUNT(*) AS row_count FROM Sports
UNION ALL SELECT 'Students', COUNT(*) FROM Students
UNION ALL SELECT 'Players', COUNT(*) FROM Players
UNION ALL SELECT 'Non-player Students', COUNT(*) FROM Students s
  WHERE NOT EXISTS (SELECT 1 FROM Players p WHERE p.student_id = s.student_id);
