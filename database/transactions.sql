-- Transaction demonstration: record one score and result per match entry.
-- MySQL 8.0.16+. Edit the IDs and values before use.
-- Run statements in order in one connection. If any step fails, stop and run
-- ROLLBACK; in that same connection. Run COMMIT; only after verification.
USE sports_tournament_management;

SET @match_id := 0;
SET @entry_id_a := 0;
SET @entry_id_b := 0;
SET @score_a := 0.000;
SET @score_b := 0.000;

START TRANSACTION;

-- Lock and confirm the selected match is not already finalized.
SELECT match_id, status
FROM Matches
WHERE match_id = @match_id
  AND status IN ('scheduled', 'live')
FOR UPDATE;

-- Confirm these are the match's only two participants before inserting.
SELECT me.entry_id
FROM Match_Entries me
WHERE me.match_id = @match_id
ORDER BY me.entry_id;

INSERT INTO Match_Scores (
    match_id, entry_id, segment_number, segment_label,
    numeric_value, text_value
)
VALUES
    (@match_id, @entry_id_a, 1, 'Final', @score_a, NULL),
    (@match_id, @entry_id_b, 1, 'Final', @score_b, NULL);

INSERT INTO Match_Results (
    match_id, entry_id, outcome, result_rank, official_note
)
VALUES
    (@match_id, @entry_id_a, 'win', NULL, 'Official result'),
    (@match_id, @entry_id_b, 'loss', NULL, 'Official result');

UPDATE Matches AS m
SET status = 'completed'
WHERE m.match_id = @match_id
  AND m.status IN ('scheduled', 'live')
  AND (
      SELECT COUNT(*)
      FROM Match_Entries me
      WHERE me.match_id = m.match_id
  ) = 2
  AND NOT EXISTS (
      SELECT 1
      FROM Match_Entries me
      LEFT JOIN Match_Results result_row
        ON result_row.match_id = me.match_id
       AND result_row.entry_id = me.entry_id
      WHERE me.match_id = m.match_id
        AND result_row.match_id IS NULL
  );

SELECT match_id, status
FROM Matches
WHERE match_id = @match_id;

-- Commit only if all statements succeeded and status is 'completed'.
-- Otherwise run ROLLBACK; in this connection.
-- COMMIT;
-- ROLLBACK;
