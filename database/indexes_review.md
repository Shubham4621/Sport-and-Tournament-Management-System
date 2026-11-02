# Index review

Static review of `schema.sql` only; no live metadata or `EXPLAIN` plans were
checked. No additional indexes are recommended.

Existing indexes already support the main application lookups:

- Tournament discovery and fixture schedules:
  `Tournaments(is_published, status, start_date)`,
  `Matches(tournament_id, status, scheduled_at)`.
- Tournament entry listings:
  `Tournament_Entries(tournament_id, status)`.
- Match participants and scores:
  `Match_Entries(match_id, entry_id)`,
  `Match_Scores(match_id, entry_id, segment_number)`.
- Results and standings:
  `Match_Results(match_id, outcome, result_rank)`,
  `Match_Results(entry_id)`.
- Player sport eligibility and team rosters:
  `Player_Sports(sport_id, player_id)`,
  `Team_Memberships(player_id, membership_to)`.

The schema also defines the necessary primary, unique, and foreign-key
indexes. Avoid adding duplicates. If performance later requires tuning,
inspect live indexes and use `EXPLAIN` with representative data first.
