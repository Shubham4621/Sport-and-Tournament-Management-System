-- Application views for MySQL 8.0.16+.
-- Tournament views expose only published tournaments and active sports.
-- Public callers should be granted access to these views, not base tables.
USE sports_tournament_management;

CREATE OR REPLACE VIEW vw_published_tournaments AS
SELECT t.tournament_id,
       t.name AS tournament_name,
       sp.sport_id,
       sp.name AS sport_name,
       t.competition_format,
       t.season,
       t.start_date,
       t.end_date,
       t.status AS tournament_status,
       t.description
FROM Tournaments t
JOIN Sports sp ON sp.sport_id = t.sport_id
WHERE t.is_published = TRUE
  AND sp.is_active = TRUE;

CREATE OR REPLACE VIEW vw_tournament_participants AS
SELECT t.tournament_id,
       t.name AS tournament_name,
       t.season,
       t.competition_format,
       te.entry_id,
       te.status AS entry_status,
       te.registered_at,
       CASE
           WHEN te.team_id IS NOT NULL THEN 'team'
           ELSE 'individual'
       END AS participant_type,
       team.team_id,
       team.name AS team_name,
       p.player_id,
       CONCAT_WS(' ', s.first_name, s.last_name) AS player_name
FROM Tournaments t
JOIN Sports sp ON sp.sport_id = t.sport_id
JOIN Tournament_Entries te ON te.tournament_id = t.tournament_id
LEFT JOIN Teams team
    ON team.team_id = te.team_id
   AND team.is_active = TRUE
LEFT JOIN Players p ON p.player_id = te.player_id
LEFT JOIN Students s ON s.student_id = p.student_id
WHERE t.is_published = TRUE
  AND sp.is_active = TRUE
  AND te.status = 'registered'
  AND (te.team_id IS NULL OR team.team_id IS NOT NULL);

-- One row per match. Participants are aggregated before joining to avoid
-- multiplying matches when a fixture has several entries.
CREATE OR REPLACE VIEW vw_match_schedule AS
WITH participant_summary AS (
    SELECT me.match_id,
           COUNT(*) AS participant_count,
           GROUP_CONCAT(
               CASE
                   WHEN te.team_id IS NOT NULL AND team.team_id IS NULL
                       THEN 'Unavailable team'
                   WHEN te.team_id IS NOT NULL THEN team.name
                   ELSE CONCAT_WS(' ', s.first_name, s.last_name)
               END
               ORDER BY me.entry_id
               SEPARATOR ', '
           ) AS participants
    FROM Match_Entries me
    JOIN Tournament_Entries te ON te.entry_id = me.entry_id
    LEFT JOIN Teams team
        ON team.team_id = te.team_id
       AND team.is_active = TRUE
    LEFT JOIN Players p ON p.player_id = te.player_id
    LEFT JOIN Students s ON s.student_id = p.student_id
    GROUP BY me.match_id
)
SELECT m.match_id,
       t.tournament_id,
       t.name AS tournament_name,
       t.season,
       sp.name AS sport_name,
       t.competition_format,
       m.match_number,
       m.stage,
       m.round_name,
       m.scheduled_at,
       m.venue,
       m.status AS match_status,
       COALESCE(ps.participant_count, 0) AS participant_count,
       ps.participants
FROM Matches m
JOIN Tournaments t ON t.tournament_id = m.tournament_id
JOIN Sports sp ON sp.sport_id = t.sport_id
LEFT JOIN participant_summary ps ON ps.match_id = m.match_id
WHERE t.is_published = TRUE
  AND sp.is_active = TRUE;

-- Scores are aggregated independently from results, so multiple score
-- segments cannot duplicate a declared result.
CREATE OR REPLACE VIEW vw_completed_match_results AS
WITH score_summary AS (
    SELECT score.match_id,
           score.entry_id,
           GROUP_CONCAT(
               CONCAT(
                   COALESCE(score.segment_label,
                            CONCAT('Segment ', score.segment_number)),
                   ': ',
                   COALESCE(CAST(score.numeric_value AS CHAR),
                            score.text_value)
               )
               ORDER BY score.segment_number
               SEPARATOR '; '
           ) AS score_summary
    FROM Match_Scores score
    GROUP BY score.match_id, score.entry_id
)
SELECT m.match_id,
       t.tournament_id,
       t.name AS tournament_name,
       t.season,
       sp.name AS sport_name,
       m.match_number,
       m.stage,
       m.round_name,
       m.scheduled_at,
       m.venue,
       me.entry_id,
       CASE
           WHEN te.team_id IS NOT NULL THEN 'team'
           ELSE 'individual'
       END AS participant_type,
       team.team_id,
       team.name AS team_name,
       p.player_id,
       CONCAT_WS(' ', s.first_name, s.last_name) AS player_name,
       result_row.outcome,
       result_row.result_rank,
       result_row.official_note,
       result_row.declared_at,
       score_summary.score_summary
FROM Matches m
JOIN Tournaments t ON t.tournament_id = m.tournament_id
JOIN Sports sp ON sp.sport_id = t.sport_id
JOIN Match_Entries me ON me.match_id = m.match_id
JOIN Tournament_Entries te ON te.entry_id = me.entry_id
JOIN Match_Results result_row
    ON result_row.match_id = me.match_id
   AND result_row.entry_id = me.entry_id
LEFT JOIN Teams team
    ON team.team_id = te.team_id
   AND team.is_active = TRUE
LEFT JOIN Players p ON p.player_id = te.player_id
LEFT JOIN Students s ON s.student_id = p.student_id
LEFT JOIN score_summary
    ON score_summary.match_id = me.match_id
   AND score_summary.entry_id = me.entry_id
WHERE m.status = 'completed'
  AND t.is_published = TRUE
  AND sp.is_active = TRUE
  AND (te.team_id IS NULL OR team.team_id IS NOT NULL);

-- A result is one completed match for an entry. Team points use configured
-- rules, defaulting to the schema's 3/1/0 defaults if no rules row exists.
-- Individual standings expose the best declared rank and record counts;
-- points are NULL because the schema defines no individual points formula.
CREATE OR REPLACE VIEW vw_tournament_standings AS
WITH completed_results AS (
    SELECT m.tournament_id,
           me.entry_id,
           m.match_id,
           LOWER(TRIM(result_row.outcome)) AS outcome,
           result_row.result_rank
    FROM Matches m
    JOIN Match_Entries me ON me.match_id = m.match_id
    JOIN Match_Results result_row
        ON result_row.match_id = me.match_id
       AND result_row.entry_id = me.entry_id
    WHERE m.status = 'completed'
),
entry_totals AS (
    SELECT t.tournament_id,
           t.name AS tournament_name,
           t.season,
           t.competition_format,
           te.entry_id,
           te.team_id,
           team.name AS team_name,
           te.player_id,
           CONCAT_WS(' ', s.first_name, s.last_name) AS player_name,
           SUM(
               CASE
                   WHEN cr.match_id IS NOT NULL
                    AND cr.outcome NOT IN ('did not start', 'dns')
                       THEN 1
                   ELSE 0
               END
           ) AS played_matches,
           SUM(CASE WHEN cr.outcome = 'win' THEN 1 ELSE 0 END) AS wins,
           SUM(CASE WHEN cr.outcome = 'loss' THEN 1 ELSE 0 END) AS losses,
           SUM(CASE WHEN cr.outcome = 'draw' THEN 1 ELSE 0 END) AS draws,
           MIN(cr.result_rank) AS best_result_rank,
           CASE
               WHEN t.competition_format = 'team' THEN
                   CAST(SUM(
                       CASE
                           WHEN cr.outcome = 'win'
                               THEN COALESCE(rules.points_for_win, 3.00)
                           WHEN cr.outcome = 'draw'
                               THEN COALESCE(rules.points_for_draw, 1.00)
                           WHEN cr.outcome = 'loss'
                               THEN COALESCE(rules.points_for_loss, 0.00)
                           ELSE 0.00
                       END
                   ) AS DECIMAL(12,2))
               ELSE NULL
           END AS total_points
    FROM Tournaments t
    JOIN Sports sp ON sp.sport_id = t.sport_id
    JOIN Tournament_Entries te
        ON te.tournament_id = t.tournament_id
       AND te.status = 'registered'
    LEFT JOIN Teams team
        ON team.team_id = te.team_id
       AND team.is_active = TRUE
    LEFT JOIN Players p ON p.player_id = te.player_id
    LEFT JOIN Students s ON s.student_id = p.student_id
    LEFT JOIN Tournament_Scoring_Rules rules
        ON rules.tournament_id = t.tournament_id
    LEFT JOIN completed_results cr
        ON cr.tournament_id = t.tournament_id
       AND cr.entry_id = te.entry_id
    WHERE t.is_published = TRUE
      AND sp.is_active = TRUE
      AND (te.team_id IS NULL OR team.team_id IS NOT NULL)
    GROUP BY t.tournament_id, t.name, t.season, t.competition_format,
             te.entry_id, te.team_id, team.name, te.player_id,
             s.first_name, s.last_name, rules.points_for_win,
             rules.points_for_draw, rules.points_for_loss
),
ranked_entries AS (
    SELECT entry_totals.*,
           RANK() OVER (
               PARTITION BY tournament_id
               ORDER BY
                   CASE
                       WHEN competition_format = 'individual'
                        AND best_result_rank IS NULL THEN 1
                       ELSE 0
                   END,
                   CASE WHEN competition_format = 'team'
                        THEN total_points END DESC,
                   CASE WHEN competition_format = 'individual'
                        THEN best_result_rank END ASC,
                   CASE WHEN competition_format = 'team'
                        THEN wins END DESC,
                   CASE WHEN competition_format = 'team'
                        THEN draws END DESC,
                   CASE WHEN competition_format = 'team'
                        THEN losses END ASC
           ) AS standings_rank
    FROM entry_totals
)
SELECT tournament_id,
       tournament_name,
       season,
       competition_format,
       standings_rank,
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
FROM ranked_entries;
