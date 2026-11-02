import re

from flask import Blueprint, jsonify, request

from .db import execute, fetch_all, fetch_one, fetch_procedure_rows


api = Blueprint("api", __name__)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
STUDENT_FIELDS = (
    "student_number",
    "first_name",
    "last_name",
    "email",
    "department_id",
    "enrollment_status",
)


def _positive_id(value, field="id"):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0 or str(parsed) != str(value).strip():
        return None
    return parsed


def _json_object():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None
    return data


def _query_boolean(name, default=False):
    value = request.args.get(name)
    if value is None:
        return default, None
    if value.lower() not in ("true", "false"):
        return None, f"{name} must be true or false."
    return value.lower() == "true", None


def _student_values(data):
    if not isinstance(data, dict):
        return None, "A JSON object is required."
    missing = [
        field
        for field in ("student_number", "first_name", "last_name", "enrollment_status")
        if field not in data
    ]
    if missing:
        return None, "Missing required field(s): " + ", ".join(missing)
    values = {}
    limits = {
        "student_number": 50,
        "first_name": 100,
        "last_name": 100,
        "enrollment_status": 30,
    }
    for field, limit in limits.items():
        value = data[field]
        if not isinstance(value, str) or not value.strip():
            return None, f"{field} must be a non-empty string."
        value = value.strip()
        if len(value) > limit:
            return None, f"{field} must be at most {limit} characters."
        values[field] = value

    email = data.get("email")
    if email is not None:
        if not isinstance(email, str) or len(email.strip()) > 254:
            return None, "email must be a valid string of at most 254 characters."
        email = email.strip() or None
        if email is not None and not EMAIL_PATTERN.match(email):
            return None, "email must be a valid email address."
    values["email"] = email

    department_id = data.get("department_id")
    if department_id in ("", None):
        values["department_id"] = None
    else:
        parsed_department_id = _positive_id(department_id)
        if parsed_department_id is None:
            return None, "department_id must be a positive integer or null."
        values["department_id"] = parsed_department_id
    return values, None


@api.get("/health")
def health():
    row = fetch_one("SELECT 1 AS database_connected")
    return jsonify(status="ok", database="connected" if row else "unavailable")


@api.get("/dashboard/stats")
def dashboard_stats():
    stats = fetch_one(
        """
        SELECT
            (SELECT COUNT(*) FROM Students) AS students,
            (SELECT COUNT(*) FROM Players) AS total_players,
            (SELECT COUNT(*) FROM Players WHERE is_active = TRUE) AS active_players,
            (SELECT COUNT(*) FROM Teams) AS total_teams,
            (SELECT COUNT(*) FROM Teams WHERE is_active = TRUE) AS active_teams,
            (SELECT COUNT(*) FROM Tournaments) AS total_tournaments,
            (SELECT COUNT(*) FROM Tournaments WHERE is_published = TRUE) AS published_tournaments,
            (SELECT COUNT(*) FROM Matches) AS total_matches,
            (SELECT COUNT(*) FROM Matches WHERE status = 'scheduled') AS scheduled_matches,
            (SELECT COUNT(*) FROM Matches WHERE status = 'live') AS live_matches,
            (SELECT COUNT(*) FROM Matches WHERE status = 'completed') AS completed_matches,
            (SELECT COUNT(*) FROM Tournament_Entries
             WHERE status = 'registered') AS tournament_participants,
            (SELECT COUNT(*) FROM Match_Results) AS total_match_results
        """
    )
    return jsonify(stats=stats)


@api.get("/students")
def list_students():
    page = _positive_id(request.args.get("page", "1"), "page")
    per_page = _positive_id(request.args.get("per_page", "25"), "per_page")
    if page is None or per_page is None or per_page > 100:
        return jsonify(error="page must be positive and per_page must be 1-100."), 400
    search = request.args.get("search", "").strip()
    if len(search) > 100:
        return jsonify(error="search must be at most 100 characters."), 400
    where = []
    params = []
    if search:
        where.append("""
        (s.student_number LIKE %s
           OR s.first_name LIKE %s
           OR s.last_name LIKE %s
           OR s.email LIKE %s)
        """)
        pattern = f"%{search}%"
        params.extend([pattern] * 4)
    department_id = request.args.get("department_id")
    if department_id is not None:
        parsed_department_id = _positive_id(department_id, "department_id")
        if parsed_department_id is None:
            return jsonify(error="department_id must be a positive integer."), 400
        where.append("s.department_id = %s")
        params.append(parsed_department_id)
    enrollment_status = request.args.get("enrollment_status")
    if enrollment_status is not None:
        enrollment_status = enrollment_status.strip()
        if not enrollment_status or len(enrollment_status) > 30:
            return jsonify(error="enrollment_status must be 1-30 characters."), 400
        where.append("s.enrollment_status = %s")
        params.append(enrollment_status)
    has_player = request.args.get("has_player")
    if has_player is not None:
        if has_player.lower() not in ("true", "false"):
            return jsonify(error="has_player must be true or false."), 400
        exists = "EXISTS" if has_player.lower() == "true" else "NOT EXISTS"
        where.append(
            f"{exists} (SELECT 1 FROM Players p WHERE p.student_id = s.student_id)"
        )
    sport_id = request.args.get("sport_id")
    if sport_id is not None:
        parsed_sport_id = _positive_id(sport_id, "sport_id")
        if parsed_sport_id is None:
            return jsonify(error="sport_id must be a positive integer."), 400
        where.append(
            """
            EXISTS (
                SELECT 1 FROM Players p
                JOIN Player_Sports ps ON ps.player_id = p.player_id
                WHERE p.student_id = s.student_id AND ps.sport_id = %s
            )
            """
        )
        params.append(parsed_sport_id)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    total_row = fetch_one(
        f"SELECT COUNT(*) AS total FROM Students s {where_sql}",
        tuple(params),
    )
    rows = fetch_all(
        f"""
        SELECT s.student_id, p.player_id, s.student_number, s.first_name, s.last_name,
               s.email, s.department_id, d.department_name,
               s.enrollment_status, s.created_at
        FROM Students s
        LEFT JOIN Departments d ON d.department_id = s.department_id
        LEFT JOIN Players p ON p.student_id = s.student_id
        {where_sql}
        ORDER BY s.student_id
        LIMIT %s OFFSET %s
        """,
        tuple(params + [per_page, (page - 1) * per_page]),
    )
    return jsonify(
        items=rows,
        page=page,
        per_page=per_page,
        total=total_row["total"],
    )


@api.post("/students")
def create_student():
    values, error = _student_values(_json_object())
    if error:
        return jsonify(error=error), 400
    student_id = execute(
        """
        INSERT INTO Students (
            student_number, first_name, last_name, email,
            department_id, enrollment_status
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        tuple(values[field] for field in STUDENT_FIELDS),
    )
    student = _get_student(student_id)
    return jsonify(student=student), 201


@api.get("/students/<int:student_id>")
def get_student(student_id):
    student = _get_student(student_id)
    if student is None:
        return jsonify(error="Student not found."), 404
    player = fetch_one(
        "SELECT player_id, is_active FROM Players WHERE student_id = %s",
        (student_id,),
    )
    eligibility = []
    if player:
        eligibility = fetch_all(
            """
            SELECT ps.sport_id, sp.name AS sport_name, ps.eligible_from,
                   ps.eligible_to
            FROM Player_Sports ps JOIN Sports sp ON sp.sport_id = ps.sport_id
            WHERE ps.player_id = %s ORDER BY sp.name
            """,
            (player["player_id"],),
        )
    return jsonify(student=student, player=player, eligibility=eligibility)


@api.put("/students/<int:student_id>")
def update_student(student_id):
    values, error = _student_values(_json_object())
    if error:
        return jsonify(error=error), 400
    if _get_student(student_id) is None:
        return jsonify(error="Student not found."), 404
    execute(
        """
        UPDATE Students
        SET student_number = %s, first_name = %s, last_name = %s,
            email = %s, department_id = %s, enrollment_status = %s
        WHERE student_id = %s
        """,
        tuple(values[field] for field in STUDENT_FIELDS) + (student_id,),
    )
    return jsonify(student=_get_student(student_id))


def _get_student(student_id):
    return fetch_one(
        """
        SELECT s.student_id, s.student_number, s.first_name, s.last_name,
               s.email, s.department_id, d.department_name,
               s.enrollment_status, s.created_at
        FROM Students s
        LEFT JOIN Departments d ON d.department_id = s.department_id
        WHERE s.student_id = %s
        """,
        (student_id,),
    )


@api.get("/sports")
def list_sports():
    include_inactive, error = _query_boolean("include_inactive")
    if error:
        return jsonify(error=error), 400
    return jsonify(
        items=fetch_all(
            f"""
            SELECT sport_id, name, description, is_active
            FROM Sports
            {"WHERE is_active = TRUE" if not include_inactive else ""}
            ORDER BY name
            """
        )
    )


@api.get("/departments")
def list_departments():
    return jsonify(
        items=fetch_all(
            """
            SELECT department_id, department_name, description
            FROM Departments
            ORDER BY department_name
            """
        )
    )


@api.get("/teams")
def list_teams():
    include_inactive, error = _query_boolean("include_inactive")
    if error:
        return jsonify(error=error), 400
    return jsonify(
        items=fetch_all(
            f"""
            SELECT team.team_id, team.name, team.team_code, team.sport_id,
                   sp.name AS sport_name, team.department_id,
                   d.department_name, team.is_active, team.created_at
            FROM Teams team
            JOIN Sports sp ON sp.sport_id = team.sport_id
            JOIN Departments d ON d.department_id = team.department_id
            {"WHERE team.is_active = TRUE AND sp.is_active = TRUE" if not include_inactive else ""}
            ORDER BY sp.name, d.department_name, team.name
            """
        )
    )


@api.get("/tournaments")
def list_tournaments():
    include_unpublished, error = _query_boolean("include_unpublished")
    if error:
        return jsonify(error=error), 400
    if include_unpublished:
        rows = fetch_all(
            """
            SELECT t.tournament_id, t.name AS tournament_name, t.sport_id,
                   sp.name AS sport_name, t.competition_format, t.season,
                   t.start_date, t.end_date, t.status AS tournament_status,
                   t.is_published, t.description,
                   rules.points_for_win, rules.points_for_draw,
                   rules.points_for_loss
            FROM Tournaments t JOIN Sports sp ON sp.sport_id = t.sport_id
            LEFT JOIN Tournament_Scoring_Rules rules
                ON rules.tournament_id = t.tournament_id
            ORDER BY t.start_date, t.name
            """
        )
    else:
        rows = fetch_all(
            """
        SELECT tournament_id, tournament_name, sport_id, sport_name,
               competition_format, season, start_date, end_date,
               tournament_status, description
        FROM vw_published_tournaments
        ORDER BY start_date, tournament_name
        """
        )
    return jsonify(items=rows)


@api.get("/tournaments/<int:tournament_id>")
def get_tournament(tournament_id):
    include_unpublished, error = _query_boolean("include_unpublished")
    if error:
        return jsonify(error=error), 400
    if include_unpublished:
        tournament = fetch_one(
            """
            SELECT t.tournament_id, t.name AS tournament_name, t.sport_id,
                   sp.name AS sport_name, t.competition_format, t.season,
                   t.start_date, t.end_date, t.status AS tournament_status,
                   t.is_published, t.description,
                   rules.points_for_win, rules.points_for_draw,
                   rules.points_for_loss
            FROM Tournaments t JOIN Sports sp ON sp.sport_id = t.sport_id
            LEFT JOIN Tournament_Scoring_Rules rules
                ON rules.tournament_id = t.tournament_id
            WHERE t.tournament_id = %s
            """,
            (tournament_id,),
        )
    else:
        tournament = fetch_one(
            """
        SELECT tournament_id, tournament_name, sport_id, sport_name,
               competition_format, season, start_date, end_date,
               tournament_status, description
        FROM vw_published_tournaments
        WHERE tournament_id = %s
        """,
            (tournament_id,),
        )
    if tournament is None:
        return jsonify(error="Tournament not found."), 404
    if include_unpublished:
        participants = fetch_all(
            """
            SELECT te.entry_id, te.status AS entry_status,
                   CASE WHEN te.team_id IS NOT NULL THEN 'team' ELSE 'individual' END
                       AS participant_type,
                   team.team_id, team.name AS team_name, p.player_id,
                   CONCAT_WS(' ', s.first_name, s.last_name) AS player_name
            FROM Tournament_Entries te
            LEFT JOIN Teams team ON team.team_id = te.team_id
            LEFT JOIN Players p ON p.player_id = te.player_id
            LEFT JOIN Students s ON s.student_id = p.student_id
            WHERE te.tournament_id = %s
            ORDER BY te.entry_id
            """,
            (tournament_id,),
        )
    else:
        participants = fetch_all(
            """
        SELECT entry_id, entry_status, participant_type, team_id, team_name,
               player_id, player_name
        FROM vw_tournament_participants
        WHERE tournament_id = %s
        ORDER BY entry_id
        """,
            (tournament_id,),
        )
    return jsonify(tournament=tournament, participants=participants)


@api.get("/matches")
def list_matches():
    include_unpublished, error = _query_boolean("include_unpublished")
    if error:
        return jsonify(error=error), 400
    tournament_id = request.args.get("tournament_id")
    clauses = []
    params = []
    if tournament_id is not None:
        parsed_id = _positive_id(tournament_id, "tournament_id")
        if parsed_id is None:
            return jsonify(error="tournament_id must be a positive integer."), 400
        clauses.append("tournament_id = %s")
        params.append(parsed_id)
    match_status = request.args.get("status")
    if match_status is not None:
        if match_status not in ("scheduled", "live", "completed", "postponed", "cancelled"):
            return jsonify(error="status is not a supported match status."), 400
        clauses.append("match_status = %s")
        params.append(match_status)

    if include_unpublished:
        admin_clauses = []
        if tournament_id is not None:
            admin_clauses.append("m.tournament_id = %s")
        if match_status is not None:
            admin_clauses.append("m.status = %s")
        where_sql = f"WHERE {' AND '.join(admin_clauses)}" if admin_clauses else ""
        rows = fetch_all(
            f"""
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
                           ORDER BY me.entry_id SEPARATOR ', '
                       ) AS participants
                FROM Match_Entries me
                JOIN Tournament_Entries te ON te.entry_id = me.entry_id
                LEFT JOIN Teams team ON team.team_id = te.team_id
                LEFT JOIN Players p ON p.player_id = te.player_id
                LEFT JOIN Students s ON s.student_id = p.student_id
                GROUP BY me.match_id
            )
            SELECT m.match_id, t.tournament_id, t.name AS tournament_name,
                   t.season, sp.name AS sport_name, t.competition_format,
                   m.match_number, m.stage, m.round_name, m.scheduled_at,
                   m.venue, m.status AS match_status,
                   COALESCE(ps.participant_count, 0) AS participant_count,
                   ps.participants
            FROM Matches m
            JOIN Tournaments t ON t.tournament_id = m.tournament_id
            JOIN Sports sp ON sp.sport_id = t.sport_id
            LEFT JOIN participant_summary ps ON ps.match_id = m.match_id
            {where_sql}
            ORDER BY m.scheduled_at, t.name, m.match_number
            """,
            tuple(params),
        )
    else:
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = fetch_all(
            f"""
            SELECT match_id, tournament_id, tournament_name, season,
                   sport_name, competition_format, match_number, stage,
                   round_name, scheduled_at, venue, match_status,
                   participant_count, participants
            FROM vw_match_schedule
            {where_sql}
            ORDER BY scheduled_at, tournament_name, match_number
            """,
            tuple(params),
        )
    return jsonify(items=rows)


@api.get("/matches/<int:match_id>")
def get_match(match_id):
    include_unpublished, error = _query_boolean("include_unpublished")
    if error:
        return jsonify(error=error), 400
    if include_unpublished:
        match = fetch_one(
            """
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
                           ORDER BY me.entry_id SEPARATOR ', '
                       ) AS participants
                FROM Match_Entries me
                JOIN Tournament_Entries te ON te.entry_id = me.entry_id
                LEFT JOIN Teams team ON team.team_id = te.team_id
                LEFT JOIN Players p ON p.player_id = te.player_id
                LEFT JOIN Students s ON s.student_id = p.student_id
                GROUP BY me.match_id
            )
            SELECT m.match_id, t.tournament_id, t.name AS tournament_name,
                   t.season, sp.name AS sport_name, t.competition_format,
                   m.match_number, m.stage, m.round_name, m.scheduled_at,
                   m.venue, m.status AS match_status,
                   COALESCE(ps.participant_count, 0) AS participant_count,
                   ps.participants
            FROM Matches m
            JOIN Tournaments t ON t.tournament_id = m.tournament_id
            JOIN Sports sp ON sp.sport_id = t.sport_id
            LEFT JOIN participant_summary ps ON ps.match_id = m.match_id
            WHERE m.match_id = %s
            """,
            (match_id,),
        )
    else:
        match = fetch_one(
            """
            SELECT match_id, tournament_id, tournament_name, season, sport_name,
                   competition_format, match_number, stage, round_name,
                   scheduled_at, venue, match_status, participant_count,
                   participants
            FROM vw_match_schedule
            WHERE match_id = %s
            """,
            (match_id,),
        )
    if match is None:
        return jsonify(error="Match not found."), 404
    return jsonify(match=match)


@api.get("/matches/<int:match_id>/results")
def match_results(match_id):
    include_unpublished, error = _query_boolean("include_unpublished")
    if error:
        return jsonify(error=error), 400
    if include_unpublished:
        rows = fetch_all(
            """
        WITH score_summary AS (
            SELECT score.match_id, score.entry_id,
                   GROUP_CONCAT(
                       CONCAT(
                           COALESCE(score.segment_label,
                                    CONCAT('Segment ', score.segment_number)),
                           ': ',
                           COALESCE(CAST(score.numeric_value AS CHAR), score.text_value)
                       )
                       ORDER BY score.segment_number SEPARATOR '; '
                   ) AS score_summary
            FROM Match_Scores score
            GROUP BY score.match_id, score.entry_id
        )
        SELECT m.match_id, t.tournament_id, t.name AS tournament_name,
               m.match_number, me.entry_id,
               CASE WHEN te.team_id IS NOT NULL THEN 'team' ELSE 'individual' END
                   AS participant_type,
               te.team_id, team.name AS team_name, te.player_id,
               CONCAT_WS(' ', s.first_name, s.last_name) AS player_name,
               result_row.outcome, result_row.result_rank,
               result_row.official_note, result_row.declared_at,
               score_summary.score_summary
        FROM Matches m
        JOIN Tournaments t ON t.tournament_id = m.tournament_id
        JOIN Match_Entries me ON me.match_id = m.match_id
        JOIN Tournament_Entries te ON te.entry_id = me.entry_id
        JOIN Match_Results result_row
          ON result_row.match_id = me.match_id
         AND result_row.entry_id = me.entry_id
        LEFT JOIN Teams team ON team.team_id = te.team_id
        LEFT JOIN Players p ON p.player_id = te.player_id
        LEFT JOIN Students s ON s.student_id = p.student_id
        LEFT JOIN score_summary
          ON score_summary.match_id = me.match_id
         AND score_summary.entry_id = me.entry_id
        WHERE m.match_id = %s AND m.status = 'completed'
        ORDER BY me.entry_id
        """,
            (match_id,),
        )
    else:
        rows = fetch_all(
            """
        SELECT match_id, tournament_id, tournament_name, match_number,
               entry_id, participant_type, team_id, team_name, player_id,
               player_name, outcome, result_rank, official_note, declared_at,
               score_summary
        FROM vw_completed_match_results
        WHERE match_id = %s
        ORDER BY entry_id
        """,
            (match_id,),
        )
    if not rows:
        visible_match = (
            fetch_one("SELECT match_id FROM Matches WHERE match_id = %s", (match_id,))
            if include_unpublished
            else fetch_one(
                "SELECT match_id FROM vw_match_schedule WHERE match_id = %s",
                (match_id,),
            )
        )
        if visible_match is None:
            return jsonify(error="Match not found."), 404
    return jsonify(match_id=match_id, results=rows)


@api.get("/tournaments/<int:tournament_id>/standings")
def tournament_standings(tournament_id):
    visible_tournament = fetch_one(
        """
        SELECT tournament_id
        FROM vw_published_tournaments
        WHERE tournament_id = %s
        """,
        (tournament_id,),
    )
    if visible_tournament is None:
        return jsonify(error="Tournament not found."), 404
    standings = fetch_procedure_rows(
        "CALL sp_get_tournament_standings(%s)",
        (tournament_id,),
    )
    return jsonify(tournament_id=tournament_id, standings=standings)
