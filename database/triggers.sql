-- Cross-table integrity checks not expressible by existing CHECK constraints.
-- MySQL 8.0.16+. Existing foreign keys and CHECK constraints remain in force.
USE sports_tournament_management;

DROP TRIGGER IF EXISTS bi_tournament_entries_validate;
DROP TRIGGER IF EXISTS bu_tournament_entries_validate;
DROP TRIGGER IF EXISTS bi_match_entries_same_tournament;
DROP TRIGGER IF EXISTS bu_match_entries_same_tournament;
DROP TRIGGER IF EXISTS bi_team_memberships_eligibility;
DROP TRIGGER IF EXISTS bu_team_memberships_eligibility;

DELIMITER $$

CREATE TRIGGER bi_tournament_entries_validate
BEFORE INSERT ON Tournament_Entries
FOR EACH ROW
BEGIN
    IF NEW.team_id IS NOT NULL AND NOT EXISTS (
        SELECT 1
        FROM Tournaments t
        JOIN Teams team ON team.team_id = NEW.team_id
        WHERE t.tournament_id = NEW.tournament_id
          AND t.competition_format = 'team'
          AND team.sport_id = t.sport_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT =
                'Team entry must match the tournament format and sport.';
    END IF;

    IF NEW.player_id IS NOT NULL AND NOT EXISTS (
        SELECT 1
        FROM Tournaments t
        JOIN Player_Sports ps
          ON ps.player_id = NEW.player_id
         AND ps.sport_id = t.sport_id
         AND ps.eligible_from <= t.end_date
         AND (ps.eligible_to IS NULL OR ps.eligible_to >= t.start_date)
        WHERE t.tournament_id = NEW.tournament_id
          AND t.competition_format = 'individual'
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT =
                'Player must be eligible for the individual tournament sport and dates.';
    END IF;
END$$

CREATE TRIGGER bu_tournament_entries_validate
BEFORE UPDATE ON Tournament_Entries
FOR EACH ROW
BEGIN
    IF NEW.team_id IS NOT NULL AND NOT EXISTS (
        SELECT 1
        FROM Tournaments t
        JOIN Teams team ON team.team_id = NEW.team_id
        WHERE t.tournament_id = NEW.tournament_id
          AND t.competition_format = 'team'
          AND team.sport_id = t.sport_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT =
                'Team entry must match the tournament format and sport.';
    END IF;

    IF NEW.player_id IS NOT NULL AND NOT EXISTS (
        SELECT 1
        FROM Tournaments t
        JOIN Player_Sports ps
          ON ps.player_id = NEW.player_id
         AND ps.sport_id = t.sport_id
         AND ps.eligible_from <= t.end_date
         AND (ps.eligible_to IS NULL OR ps.eligible_to >= t.start_date)
        WHERE t.tournament_id = NEW.tournament_id
          AND t.competition_format = 'individual'
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT =
                'Player must be eligible for the individual tournament sport and dates.';
    END IF;

    IF (
        NEW.tournament_id <> OLD.tournament_id
        OR NOT (NEW.team_id <=> OLD.team_id)
        OR NOT (NEW.player_id <=> OLD.player_id)
    ) AND EXISTS (
        SELECT 1
        FROM Match_Entries me
        WHERE me.entry_id = OLD.entry_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT =
                'Do not change a tournament entry participant after it is scheduled in a match.';
    END IF;
END$$

CREATE TRIGGER bi_match_entries_same_tournament
BEFORE INSERT ON Match_Entries
FOR EACH ROW
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM Matches m
        JOIN Tournament_Entries te
          ON te.entry_id = NEW.entry_id
         AND te.tournament_id = m.tournament_id
        WHERE m.match_id = NEW.match_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT =
                'Match participant must be entered in that match tournament.';
    END IF;
END$$

CREATE TRIGGER bu_match_entries_same_tournament
BEFORE UPDATE ON Match_Entries
FOR EACH ROW
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM Matches m
        JOIN Tournament_Entries te
          ON te.entry_id = NEW.entry_id
         AND te.tournament_id = m.tournament_id
        WHERE m.match_id = NEW.match_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT =
                'Match participant must be entered in that match tournament.';
    END IF;
END$$

CREATE TRIGGER bi_team_memberships_eligibility
BEFORE INSERT ON Team_Memberships
FOR EACH ROW
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM Teams team
        JOIN Player_Sports ps
          ON ps.player_id = NEW.player_id
         AND ps.sport_id = team.sport_id
         AND ps.eligible_from <= NEW.membership_from
         AND (
             ps.eligible_to IS NULL
             OR (
                 NEW.membership_to IS NOT NULL
                 AND ps.eligible_to >= NEW.membership_to
             )
         )
        WHERE team.team_id = NEW.team_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT =
                'Player eligibility must cover the complete team membership.';
    END IF;
END$$

CREATE TRIGGER bu_team_memberships_eligibility
BEFORE UPDATE ON Team_Memberships
FOR EACH ROW
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM Teams team
        JOIN Player_Sports ps
          ON ps.player_id = NEW.player_id
         AND ps.sport_id = team.sport_id
         AND ps.eligible_from <= NEW.membership_from
         AND (
             ps.eligible_to IS NULL
             OR (
                 NEW.membership_to IS NOT NULL
                 AND ps.eligible_to >= NEW.membership_to
             )
         )
        WHERE team.team_id = NEW.team_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT =
                'Player eligibility must cover the complete team membership.';
    END IF;
END$$

DELIMITER ;
