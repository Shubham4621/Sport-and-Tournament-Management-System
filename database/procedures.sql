-- Application procedures for MySQL 8.0.16+.
-- Re-running replaces only these named procedures; it does not change rows.
USE sports_tournament_management;

DROP PROCEDURE IF EXISTS sp_get_tournament_standings;
DROP PROCEDURE IF EXISTS sp_get_tournament_report;

DELIMITER $$

CREATE PROCEDURE sp_get_tournament_standings(
    IN p_tournament_id INT UNSIGNED
)
SQL SECURITY INVOKER
READS SQL DATA
BEGIN
    IF p_tournament_id IS NULL OR p_tournament_id = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'A positive tournament ID is required.';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM vw_published_tournaments published
        WHERE published.tournament_id = p_tournament_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Published, active tournament not found.';
    END IF;

    SELECT standings_rank,
           entry_id,
           team_id,
           team_name,
           player_id,
           player_name,
           played_matches,
           wins,
           losses,
           draws,
           total_points,
           best_result_rank
    FROM vw_tournament_standings
    WHERE tournament_id = p_tournament_id
    ORDER BY standings_rank, entry_id;
END$$

CREATE PROCEDURE sp_get_tournament_report(
    IN p_tournament_id INT UNSIGNED
)
SQL SECURITY INVOKER
READS SQL DATA
BEGIN
    IF p_tournament_id IS NULL OR p_tournament_id = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'A positive tournament ID is required.';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM Tournaments t
        WHERE t.tournament_id = p_tournament_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Tournament not found.';
    END IF;

    -- Result set 1: one row per tournament; independent scalar subqueries
    -- keep participant, match, and result counts from multiplying each other.
    SELECT t.tournament_id,
           t.name AS tournament_name,
           sp.name AS sport_name,
           t.competition_format,
           t.season,
           t.start_date,
           t.end_date,
           t.status AS tournament_status,
           t.is_published,
           (
               SELECT COUNT(*)
               FROM Tournament_Entries te
               WHERE te.tournament_id = t.tournament_id
           ) AS all_entries,
           (
               SELECT COUNT(*)
               FROM Tournament_Entries te
               WHERE te.tournament_id = t.tournament_id
                 AND te.status = 'registered'
           ) AS registered_entries,
           (
               SELECT COUNT(*)
               FROM Tournament_Entries te
               WHERE te.tournament_id = t.tournament_id
                 AND te.status = 'registered'
                 AND te.team_id IS NOT NULL
           ) AS registered_teams,
           (
               SELECT COUNT(*)
               FROM Tournament_Entries te
               WHERE te.tournament_id = t.tournament_id
                 AND te.status = 'registered'
                 AND te.player_id IS NOT NULL
           ) AS registered_players,
           (
               SELECT COUNT(*)
               FROM Matches m
               WHERE m.tournament_id = t.tournament_id
           ) AS total_matches,
           (
               SELECT COUNT(*)
               FROM Matches m
               WHERE m.tournament_id = t.tournament_id
                 AND m.status = 'completed'
           ) AS completed_matches,
           (
               SELECT COUNT(*)
               FROM Matches m
               WHERE m.tournament_id = t.tournament_id
                 AND m.status = 'scheduled'
           ) AS scheduled_matches,
           (
               SELECT COUNT(*)
               FROM Match_Results result_row
               JOIN Matches m ON m.match_id = result_row.match_id
               WHERE m.tournament_id = t.tournament_id
                 AND m.status = 'completed'
           ) AS declared_results
    FROM Tournaments t
    JOIN Sports sp ON sp.sport_id = t.sport_id
    WHERE t.tournament_id = p_tournament_id;

    -- Result set 2: result outcomes for completed matches only.
    SELECT LOWER(TRIM(result_row.outcome)) AS outcome,
           COUNT(*) AS participant_results
    FROM Match_Results result_row
    JOIN Matches m ON m.match_id = result_row.match_id
    WHERE m.tournament_id = p_tournament_id
      AND m.status = 'completed'
    GROUP BY LOWER(TRIM(result_row.outcome))
    ORDER BY outcome;
END$$

DELIMITER ;
