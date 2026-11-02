import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request

from .db import (
    fetch_all,
    fetch_one,
    fetch_procedure_result_sets,
    transaction,
)


management_api = Blueprint("management_api", __name__)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TOURNAMENT_FORMATS = {"team", "individual"}
TOURNAMENT_STATUSES = {
    "planned",
    "registration",
    "in_progress",
    "completed",
    "cancelled",
}
MATCH_STATUSES = {"scheduled", "live", "completed", "postponed", "cancelled"}
RESULT_OUTCOMES = {"win", "loss", "draw", "did not start", "dns"}
UINT_MAX = 4_294_967_295


def _json_object():
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else None


def _positive_id(value):
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0 or parsed > UINT_MAX or str(parsed) != str(value).strip():
        return None
    return parsed


def _bounded_text(data, key, maximum, *, required=False, default=None):
    value = data.get(key, default)
    if value is None and not required:
        return None, None
    if not isinstance(value, str) or not value.strip():
        return None, f"{key} must be a non-empty string."
    value = value.strip()
    if len(value) > maximum:
        return None, f"{key} must be at most {maximum} characters."
    return value, None


def _optional_date(data, key, *, required=False):
    value = data.get(key)
    if value is None and not required:
        return None, None
    if not isinstance(value, str):
        return None, f"{key} must be an ISO date (YYYY-MM-DD)."
    try:
        return date.fromisoformat(value).isoformat(), None
    except ValueError:
        return None, f"{key} must be an ISO date (YYYY-MM-DD)."


def _optional_datetime(data, key, *, required=False):
    value = data.get(key)
    if value is None and not required:
        return None, None
    if not isinstance(value, str):
        return None, f"{key} must be an ISO date/time."
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None, f"{key} must be an ISO date/time."
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed.strftime("%Y-%m-%d %H:%M:%S"), None


def _boolean(data, key, *, default=None):
    value = data.get(key, default)
    if value is None and key not in data:
        return None, None
    if not isinstance(value, bool):
        return None, f"{key} must be a boolean."
    return value, None


def _decimal(data, key, default=None):
    value = data.get(key, default)
    if value is None:
        return None, None
    if isinstance(value, bool):
        return None, f"{key} must be a non-negative number."
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None, f"{key} must be a non-negative number."
    if not parsed.is_finite() or parsed < 0 or parsed > Decimal("999999.99"):
        return None, f"{key} must be between 0 and 999999.99."
    return parsed.quantize(Decimal("0.01")), None


def _required_id(data, key):
    parsed = _positive_id(data.get(key))
    if parsed is None:
        return None, f"{key} must be a positive integer."
    return parsed, None


def _validated_score_rows(scores, participant_ids):
    if not isinstance(scores, list):
        return None, "scores must be an array."
    result = []
    seen = set()
    for index, score in enumerate(scores):
        if not isinstance(score, dict):
            return None, f"scores[{index}] must be an object."
        entry_id = _positive_id(score.get("entry_id"))
        segment_number = _positive_id(score.get("segment_number"))
        if entry_id is None or entry_id not in participant_ids:
            return None, f"scores[{index}].entry_id must be a match participant."
        if segment_number is None:
            return None, f"scores[{index}].segment_number must be positive."
        if (entry_id, segment_number) in seen:
            return None, "A score may appear only once per entry and segment."
        seen.add((entry_id, segment_number))
        numeric_value = score.get("numeric_value")
        text_value = score.get("text_value")
        if (numeric_value is None) == (text_value is None):
            return None, f"scores[{index}] must provide exactly one score value."
        if numeric_value is not None:
            if isinstance(numeric_value, bool):
                return None, f"scores[{index}].numeric_value must be numeric."
            try:
                number = Decimal(str(numeric_value))
            except (InvalidOperation, ValueError):
                return None, f"scores[{index}].numeric_value must be numeric."
            if (
                not number.is_finite()
                or abs(number) > Decimal("999999999.999")
                or number.as_tuple().exponent < -3
            ):
                return None, f"scores[{index}].numeric_value exceeds DECIMAL(12,3)."
            numeric_value = number
        if text_value is not None:
            if not isinstance(text_value, str) or len(text_value) > 255:
                return None, f"scores[{index}].text_value must be at most 255 characters."
        label = score.get("segment_label")
        if label is not None and (
            not isinstance(label, str) or len(label) > 80
        ):
            return None, f"scores[{index}].segment_label must be at most 80 characters."
        result.append((entry_id, segment_number, label, numeric_value, text_value))
    return result, None


def _participant_ids(data, key="entry_ids"):
    values = data.get(key)
    if not isinstance(values, list) or len(values) < 2:
        return None, f"{key} must contain at least two match-entry IDs."
    parsed = [_positive_id(value) for value in values]
    if any(value is None for value in parsed):
        return None, f"{key} must contain positive integer IDs."
    if len(set(parsed)) != len(parsed):
        return None, f"{key} must not contain duplicates."
    return parsed, None


def _participant_rows(cursor, tournament_id, entry_ids):
    placeholders = ", ".join(["%s"] * len(entry_ids))
    cursor.execute(
        f"""
        SELECT te.entry_id, te.team_id, te.player_id, te.status,
               team.sport_id AS team_sport_id
        FROM Tournament_Entries te
        LEFT JOIN Teams team ON team.team_id = te.team_id
        WHERE te.tournament_id = %s
          AND te.entry_id IN ({placeholders})
        FOR UPDATE
        """,
        (tournament_id, *entry_ids),
    )
    return cursor.fetchall()


def _check_team_schedule_conflict(
    cursor, entry_ids, scheduled_at, exclude_match_id=None
):
    if scheduled_at is None:
        return None
    placeholders = ", ".join(["%s"] * len(entry_ids))
    cursor.execute(
        f"""
        SELECT DISTINCT te.team_id
        FROM Tournament_Entries te
        WHERE te.entry_id IN ({placeholders})
          AND te.team_id IS NOT NULL
        ORDER BY te.team_id
        """,
        tuple(entry_ids),
    )
    team_ids = [row["team_id"] for row in cursor.fetchall()]
    if not team_ids:
        return None
    team_placeholders = ", ".join(["%s"] * len(team_ids))
    cursor.execute(
        f"SELECT team_id FROM Teams WHERE team_id IN ({team_placeholders}) ORDER BY team_id FOR UPDATE",
        tuple(team_ids),
    )
    cursor.fetchall()
    exclusion = "AND m.match_id <> %s" if exclude_match_id is not None else ""
    params = [*team_ids, scheduled_at]
    if exclude_match_id is not None:
        params.append(exclude_match_id)
    cursor.execute(
        f"""
        SELECT m.match_id, te.team_id
        FROM Matches m
        JOIN Match_Entries me ON me.match_id = m.match_id
        JOIN Tournament_Entries te ON te.entry_id = me.entry_id
        WHERE te.team_id IN ({team_placeholders})
          AND m.status IN ('scheduled', 'live')
          AND m.scheduled_at = %s
          {exclusion}
        LIMIT 1
        """,
        tuple(params),
    )
    return cursor.fetchone()


def _save_scores(cursor, match_id, scores):
    for entry_id, segment_number, label, numeric_value, text_value in scores:
        cursor.execute(
            """
            INSERT INTO Match_Scores (
                match_id, entry_id, segment_number, segment_label,
                numeric_value, text_value
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                segment_label = VALUES(segment_label),
                numeric_value = VALUES(numeric_value),
                text_value = VALUES(text_value),
                recorded_at = CURRENT_TIMESTAMP
            """,
            (
                match_id,
                entry_id,
                segment_number,
                label,
                numeric_value,
                text_value,
            ),
        )


@management_api.get("/sports/<int:sport_id>")
def get_sport(sport_id):
    include_inactive = request.args.get("include_inactive", "").lower()
    if include_inactive not in ("", "true", "false"):
        return jsonify(error="include_inactive must be true or false."), 400
    active_filter = "" if include_inactive == "true" else "AND is_active = TRUE"
    sport = fetch_one(
        f"""
        SELECT sport_id, name, description, is_active, created_at
        FROM Sports
        WHERE sport_id = %s {active_filter}
        """,
        (sport_id,),
    )
    if sport is None:
        return jsonify(error="Sport not found."), 404
    return jsonify(sport=sport)


@management_api.post("/sports")
def create_sport():
    data = _json_object()
    if data is None:
        return jsonify(error="A JSON object is required."), 400
    name, error = _bounded_text(data, "name", 100, required=True)
    if error:
        return jsonify(error=error), 400
    description = data.get("description")
    if description is not None and not isinstance(description, str):
        return jsonify(error="description must be a string or null."), 400
    active, error = _boolean(data, "is_active", default=True)
    if error:
        return jsonify(error=error), 400
    sport_id = None
    with transaction() as cursor:
        cursor.execute(
            "INSERT INTO Sports (name, description, is_active) VALUES (%s, %s, %s)",
            (name, description, active),
        )
        sport_id = cursor.lastrowid
    return jsonify(sport={"sport_id": sport_id, "name": name, "description": description, "is_active": active}), 201


@management_api.put("/sports/<int:sport_id>")
def update_sport(sport_id):
    data = _json_object()
    if data is None:
        return jsonify(error="A JSON object is required."), 400
    updates = {}
    if "name" in data:
        updates["name"], error = _bounded_text(data, "name", 100, required=True)
        if error:
            return jsonify(error=error), 400
    if "description" in data:
        if data["description"] is not None and not isinstance(data["description"], str):
            return jsonify(error="description must be a string or null."), 400
        updates["description"] = data["description"]
    if "is_active" in data:
        updates["is_active"], error = _boolean(data, "is_active")
        if error:
            return jsonify(error=error), 400
    if not updates:
        return jsonify(error="At least one updatable field is required."), 400
    columns = ", ".join(f"{key} = %s" for key in updates)
    with transaction() as cursor:
        cursor.execute("SELECT sport_id FROM Sports WHERE sport_id = %s FOR UPDATE", (sport_id,))
        if cursor.fetchone() is None:
            return jsonify(error="Sport not found."), 404
        cursor.execute(
            f"UPDATE Sports SET {columns} WHERE sport_id = %s",
            (*updates.values(), sport_id),
        )
    sport = fetch_one(
        "SELECT sport_id, name, description, is_active, created_at FROM Sports WHERE sport_id = %s",
        (sport_id,),
    )
    return jsonify(sport=sport)


@management_api.delete("/sports/<int:sport_id>")
def delete_sport(sport_id):
    with transaction() as cursor:
        cursor.execute("DELETE FROM Sports WHERE sport_id = %s", (sport_id,))
        if cursor.rowcount == 0:
            return jsonify(error="Sport not found."), 404
    return jsonify(message="Sport deleted.", sport_id=sport_id)


@management_api.delete("/students/<int:student_id>")
def delete_student(student_id):
    with transaction() as cursor:
        cursor.execute("DELETE FROM Students WHERE student_id = %s", (student_id,))
        if cursor.rowcount == 0:
            return jsonify(error="Student not found."), 404
    return jsonify(message="Student deleted.", student_id=student_id)


@management_api.get("/players")
def list_players():
    page = _positive_id(request.args.get("page", "1"))
    per_page = _positive_id(request.args.get("per_page", "25"))
    if page is None or per_page is None or per_page > 100:
        return jsonify(error="page must be positive and per_page must be 1-100."), 400
    search = request.args.get("search", "").strip()
    if len(search) > 100:
        return jsonify(error="search must be at most 100 characters."), 400
    sport_id = request.args.get("sport_id")
    where = []
    params = []
    if search:
        pattern = f"%{search}%"
        where.append(
            "(s.student_number LIKE %s OR s.first_name LIKE %s OR s.last_name LIKE %s OR s.email LIKE %s)"
        )
        params.extend([pattern] * 4)
    if sport_id is not None:
        parsed_sport_id = _positive_id(sport_id)
        if parsed_sport_id is None:
            return jsonify(error="sport_id must be a positive integer."), 400
        where.append(
            "EXISTS (SELECT 1 FROM Player_Sports ps WHERE ps.player_id = p.player_id AND ps.sport_id = %s)"
        )
        params.append(parsed_sport_id)
    active = request.args.get("is_active")
    if active is not None:
        if active.lower() not in ("true", "false"):
            return jsonify(error="is_active must be true or false."), 400
        where.append("p.is_active = %s")
        params.append(active.lower() == "true")
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    total = fetch_one(
        f"""
        SELECT COUNT(*) AS total
        FROM Players p JOIN Students s ON s.student_id = p.student_id
        {where_sql}
        """,
        tuple(params),
    )["total"]
    items = fetch_all(
        f"""
        SELECT p.player_id, p.student_id, p.is_active, p.created_at,
               s.student_number, s.first_name, s.last_name, s.email,
               s.department_id, d.department_name,
               (SELECT COUNT(*) FROM Player_Sports ps WHERE ps.player_id = p.player_id)
                   AS eligible_sport_count
        FROM Players p
        JOIN Students s ON s.student_id = p.student_id
        LEFT JOIN Departments d ON d.department_id = s.department_id
        {where_sql}
        ORDER BY p.player_id
        LIMIT %s OFFSET %s
        """,
        tuple(params + [per_page, (page - 1) * per_page]),
    )
    return jsonify(items=items, page=page, per_page=per_page, total=total)


@management_api.get("/players/<int:player_id>")
def get_player(player_id):
    player = fetch_one(
        """
        SELECT p.player_id, p.student_id, p.is_active, p.created_at,
               s.student_number, s.first_name, s.last_name, s.email,
               s.department_id, d.department_name
        FROM Players p
        JOIN Students s ON s.student_id = p.student_id
        LEFT JOIN Departments d ON d.department_id = s.department_id
        WHERE p.player_id = %s
        """,
        (player_id,),
    )
    if player is None:
        return jsonify(error="Player not found."), 404
    eligibility = fetch_all(
        """
        SELECT ps.sport_id, sp.name AS sport_name, ps.eligible_from,
               ps.eligible_to, ps.created_at
        FROM Player_Sports ps
        JOIN Sports sp ON sp.sport_id = ps.sport_id
        WHERE ps.player_id = %s
        ORDER BY sp.name
        """,
        (player_id,),
    )
    return jsonify(player=player, eligibility=eligibility)


@management_api.post("/students/<int:student_id>/player")
def create_player(student_id):
    data = _json_object()
    if data is None:
        data = {}
    active, error = _boolean(data, "is_active", default=True)
    if error:
        return jsonify(error=error), 400
    with transaction() as cursor:
        cursor.execute(
            "SELECT student_id FROM Students WHERE student_id = %s FOR UPDATE",
            (student_id,),
        )
        if cursor.fetchone() is None:
            return jsonify(error="Student not found."), 404
        cursor.execute("SELECT player_id FROM Players WHERE student_id = %s", (student_id,))
        if cursor.fetchone() is not None:
            return jsonify(error="This student already has a player profile."), 409
        cursor.execute(
            "INSERT INTO Players (student_id, is_active) VALUES (%s, %s)",
            (student_id, active),
        )
        player_id = cursor.lastrowid
    return jsonify(player={"player_id": player_id, "student_id": student_id, "is_active": active}), 201


@management_api.get("/players/<int:player_id>/eligibility")
def list_player_eligibility(player_id):
    player = fetch_one("SELECT player_id FROM Players WHERE player_id = %s", (player_id,))
    if player is None:
        return jsonify(error="Player not found."), 404
    items = fetch_all(
        """
        SELECT ps.sport_id, sp.name AS sport_name, ps.eligible_from,
               ps.eligible_to, ps.created_at
        FROM Player_Sports ps JOIN Sports sp ON sp.sport_id = ps.sport_id
        WHERE ps.player_id = %s ORDER BY sp.name
        """,
        (player_id,),
    )
    return jsonify(player_id=player_id, items=items)


def _eligibility_values(data):
    eligible_from, error = _optional_date(data, "eligible_from", required=True)
    if error:
        return None, error
    eligible_to, error = _optional_date(data, "eligible_to")
    if error:
        return None, error
    if eligible_to and eligible_to < eligible_from:
        return None, "eligible_to must be on or after eligible_from."
    return (eligible_from, eligible_to), None


def _eligibility_conflicts_with_memberships(
    cursor, player_id, sport_id, eligible_from, eligible_to
):
    cursor.execute(
        """
        SELECT 1
        FROM Team_Memberships tm
        JOIN Teams team ON team.team_id = tm.team_id
        WHERE tm.player_id = %s
          AND team.sport_id = %s
          AND (
              tm.membership_from < %s
              OR (
                  %s IS NOT NULL
                  AND (
                      tm.membership_to IS NULL
                      OR tm.membership_to > %s
                  )
              )
          )
        LIMIT 1
        """,
        (
            player_id,
            sport_id,
            eligible_from,
            eligible_to,
            eligible_to,
        ),
    )
    return cursor.fetchone() is not None


@management_api.post("/players/<int:player_id>/eligibility")
def add_player_eligibility(player_id):
    data = _json_object()
    if data is None:
        return jsonify(error="A JSON object is required."), 400
    sport_id, error = _required_id(data, "sport_id")
    if error:
        return jsonify(error=error), 400
    dates, error = _eligibility_values(data)
    if error:
        return jsonify(error=error), 400
    with transaction() as cursor:
        cursor.execute("SELECT player_id FROM Players WHERE player_id = %s FOR UPDATE", (player_id,))
        if cursor.fetchone() is None:
            return jsonify(error="Player not found."), 404
        cursor.execute(
            "SELECT sport_id FROM Sports WHERE sport_id = %s AND is_active = TRUE FOR UPDATE",
            (sport_id,),
        )
        if cursor.fetchone() is None:
            return jsonify(error="Active sport not found."), 404
        cursor.execute(
            """
            INSERT INTO Player_Sports (player_id, sport_id, eligible_from, eligible_to)
            VALUES (%s, %s, %s, %s)
            """,
            (player_id, sport_id, *dates),
        )
    return jsonify(
        eligibility={
            "player_id": player_id,
            "sport_id": sport_id,
            "eligible_from": dates[0],
            "eligible_to": dates[1],
        }
    ), 201


@management_api.put("/players/<int:player_id>/eligibility/<int:sport_id>")
def update_player_eligibility(player_id, sport_id):
    data = _json_object()
    if data is None:
        return jsonify(error="A JSON object is required."), 400
    dates, error = _eligibility_values(data)
    if error:
        return jsonify(error=error), 400
    with transaction() as cursor:
        cursor.execute(
            """
            SELECT 1 FROM Player_Sports
            WHERE player_id = %s AND sport_id = %s
            FOR UPDATE
            """,
            (player_id, sport_id),
        )
        if cursor.fetchone() is None:
            return jsonify(error="Player sport eligibility not found."), 404
        if _eligibility_conflicts_with_memberships(
            cursor, player_id, sport_id, *dates
        ):
            return jsonify(
                error="Eligibility dates cannot exclude an existing team membership."
            ), 409
        cursor.execute(
            """
            UPDATE Player_Sports
            SET eligible_from = %s, eligible_to = %s
            WHERE player_id = %s AND sport_id = %s
            """,
            (*dates, player_id, sport_id),
        )
    return jsonify(
        eligibility={
            "player_id": player_id,
            "sport_id": sport_id,
            "eligible_from": dates[0],
            "eligible_to": dates[1],
        }
    )


@management_api.delete("/players/<int:player_id>/eligibility/<int:sport_id>")
def end_player_eligibility(player_id, sport_id):
    with transaction() as cursor:
        cursor.execute(
            """
            SELECT eligible_from, eligible_to
            FROM Player_Sports
            WHERE player_id = %s AND sport_id = %s
            FOR UPDATE
            """,
            (player_id, sport_id),
        )
        eligibility = cursor.fetchone()
        if eligibility is None:
            return jsonify(error="Player sport eligibility not found."), 404
        today = date.today()
        eligible_from = eligibility["eligible_from"]
        eligible_to = eligibility["eligible_to"]
        if eligible_from > today:
            return jsonify(
                error="Future eligibility cannot be ended before its effective date."
            ), 409
        if eligible_to is not None and eligible_to < today:
            return jsonify(error="Player sport eligibility has already ended."), 409
        end_date = max(eligible_from, today)
        if _eligibility_conflicts_with_memberships(
            cursor, player_id, sport_id, eligible_from, end_date
        ):
            return jsonify(
                error="End the player's team membership before ending sport eligibility."
            ), 409
        cursor.execute(
            """
            UPDATE Player_Sports SET eligible_to = %s
            WHERE player_id = %s AND sport_id = %s
            """,
            (end_date, player_id, sport_id),
        )
    return jsonify(
        message="Player sport eligibility ended.",
        player_id=player_id,
        sport_id=sport_id,
        eligible_to=end_date.isoformat(),
    )


@management_api.get("/teams/<int:team_id>")
def get_team(team_id):
    include_inactive = request.args.get("include_inactive", "").lower()
    if include_inactive not in ("", "true", "false"):
        return jsonify(error="include_inactive must be true or false."), 400
    team_filter = (
        ""
        if include_inactive == "true"
        else "AND team.is_active = TRUE AND sp.is_active = TRUE"
    )
    team = fetch_one(
        f"""
        SELECT team.team_id, team.sport_id, sp.name AS sport_name,
               team.department_id, d.department_name, team.name,
               team.team_code, team.is_active, team.created_at
        FROM Teams team
        JOIN Sports sp ON sp.sport_id = team.sport_id
        JOIN Departments d ON d.department_id = team.department_id
        WHERE team.team_id = %s {team_filter}
        """,
        (team_id,),
    )
    if team is None:
        return jsonify(error="Team not found."), 404
    history_value = request.args.get("include_history", "true").lower()
    if history_value not in ("true", "false"):
        return jsonify(error="include_history must be true or false."), 400
    history = history_value == "true"
    membership_filter = "" if history else "AND (tm.membership_to IS NULL OR tm.membership_to >= CURDATE())"
    members = fetch_all(
        f"""
        SELECT tm.player_id, tm.membership_from, tm.membership_to,
               p.student_id, s.student_number, s.first_name, s.last_name,
               s.email
        FROM Team_Memberships tm
        JOIN Players p ON p.player_id = tm.player_id
        JOIN Students s ON s.student_id = p.student_id
        WHERE tm.team_id = %s {membership_filter}
        ORDER BY tm.membership_from DESC, s.last_name, s.first_name
        """,
        (team_id,),
    )
    return jsonify(team=team, members=members)


@management_api.post("/teams")
def create_team():
    data = _json_object()
    if data is None:
        return jsonify(error="A JSON object is required."), 400
    sport_id, error = _required_id(data, "sport_id")
    if error:
        return jsonify(error=error), 400
    department_id, error = _required_id(data, "department_id")
    if error:
        return jsonify(error=error), 400
    name, error = _bounded_text(data, "name", 150, required=True)
    if error:
        return jsonify(error=error), 400
    code, error = _bounded_text(data, "team_code", 50)
    if error:
        return jsonify(error=error), 400
    active, error = _boolean(data, "is_active", default=True)
    if error:
        return jsonify(error=error), 400
    with transaction() as cursor:
        cursor.execute(
            "SELECT sport_id FROM Sports WHERE sport_id = %s FOR UPDATE",
            (sport_id,),
        )
        if cursor.fetchone() is None:
            return jsonify(error="Sport not found."), 404
        cursor.execute(
            "SELECT department_id FROM Departments WHERE department_id = %s",
            (department_id,),
        )
        if cursor.fetchone() is None:
            return jsonify(error="Department not found."), 404
        cursor.execute(
            """
            INSERT INTO Teams (sport_id, department_id, name, team_code, is_active)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (sport_id, department_id, name, code, active),
        )
        team_id = cursor.lastrowid
    return jsonify(
        team={
            "team_id": team_id,
            "sport_id": sport_id,
            "department_id": department_id,
            "name": name,
            "team_code": code,
            "is_active": active,
        }
    ), 201


@management_api.put("/teams/<int:team_id>")
def update_team(team_id):
    data = _json_object()
    if data is None:
        return jsonify(error="A JSON object is required."), 400
    updates = {}
    for key, maximum in (("name", 150), ("team_code", 50)):
        if key in data:
            updates[key], error = _bounded_text(data, key, maximum, required=key == "name")
            if error:
                return jsonify(error=error), 400
    for key in ("sport_id", "department_id"):
        if key in data:
            updates[key], error = _required_id(data, key)
            if error:
                return jsonify(error=error), 400
    if "is_active" in data:
        updates["is_active"], error = _boolean(data, "is_active")
        if error:
            return jsonify(error=error), 400
    if not updates:
        return jsonify(error="At least one updatable field is required."), 400
    with transaction() as cursor:
        cursor.execute("SELECT team_id FROM Teams WHERE team_id = %s FOR UPDATE", (team_id,))
        if cursor.fetchone() is None:
            return jsonify(error="Team not found."), 404
        if "sport_id" in updates:
            cursor.execute("SELECT sport_id FROM Sports WHERE sport_id = %s", (updates["sport_id"],))
            if cursor.fetchone() is None:
                return jsonify(error="Sport not found."), 404
            cursor.execute(
                """
                SELECT
                    EXISTS(
                        SELECT 1 FROM Team_Memberships
                        WHERE team_id = %s
                    )
                    OR EXISTS(
                        SELECT 1 FROM Tournament_Entries
                        WHERE team_id = %s
                    ) AS has_history
                """,
                (team_id, team_id),
            )
            if cursor.fetchone()["has_history"]:
                return jsonify(
                    error="A team's sport cannot change after memberships or tournament entries exist."
                ), 409
        if "department_id" in updates:
            cursor.execute(
                "SELECT department_id FROM Departments WHERE department_id = %s",
                (updates["department_id"],),
            )
            if cursor.fetchone() is None:
                return jsonify(error="Department not found."), 404
        columns = ", ".join(f"{key} = %s" for key in updates)
        cursor.execute(
            f"UPDATE Teams SET {columns} WHERE team_id = %s",
            (*updates.values(), team_id),
        )
    team = fetch_one(
        """
        SELECT team.team_id, team.sport_id, sp.name AS sport_name,
               team.department_id, d.department_name, team.name,
               team.team_code, team.is_active, team.created_at
        FROM Teams team JOIN Sports sp ON sp.sport_id = team.sport_id
        JOIN Departments d ON d.department_id = team.department_id
        WHERE team.team_id = %s
        """,
        (team_id,),
    )
    return jsonify(team=team)


@management_api.delete("/teams/<int:team_id>")
def delete_team(team_id):
    with transaction() as cursor:
        cursor.execute("DELETE FROM Teams WHERE team_id = %s", (team_id,))
        if cursor.rowcount == 0:
            return jsonify(error="Team not found."), 404
    return jsonify(message="Team deleted.", team_id=team_id)


@management_api.post("/teams/<int:team_id>/members")
def add_team_member(team_id):
    data = _json_object()
    if data is None:
        return jsonify(error="A JSON object is required."), 400
    player_id, error = _required_id(data, "player_id")
    if error:
        return jsonify(error=error), 400
    membership_from, error = _optional_date(data, "membership_from")
    if error:
        return jsonify(error=error), 400
    membership_from = membership_from or date.today().isoformat()
    membership_to, error = _optional_date(data, "membership_to")
    if error:
        return jsonify(error=error), 400
    if membership_to and membership_to < membership_from:
        return jsonify(error="membership_to must be on or after membership_from."), 400
    with transaction() as cursor:
        cursor.execute(
            """
            SELECT team_id, sport_id, is_active
            FROM Teams WHERE team_id = %s FOR UPDATE
            """,
            (team_id,),
        )
        team = cursor.fetchone()
        if team is None:
            return jsonify(error="Team not found."), 404
        if not team["is_active"]:
            return jsonify(error="Inactive teams cannot add members."), 409
        cursor.execute(
            "SELECT player_id, is_active FROM Players WHERE player_id = %s FOR UPDATE",
            (player_id,),
        )
        player = cursor.fetchone()
        if player is None:
            return jsonify(error="Player not found."), 404
        if not player["is_active"]:
            return jsonify(error="Inactive players cannot be added to teams."), 409
        cursor.execute(
            """
            SELECT 1
            FROM Team_Memberships tm
            JOIN Teams other_team ON other_team.team_id = tm.team_id
            WHERE tm.player_id = %s
              AND other_team.sport_id = %s
              AND tm.membership_from <= COALESCE(%s, '9999-12-31')
              AND (tm.membership_to IS NULL OR tm.membership_to >= %s)
            LIMIT 1
            """,
            (player_id, team["sport_id"], membership_to, membership_from),
        )
        if cursor.fetchone() is not None:
            return jsonify(
                error="The player already has an overlapping membership in this sport."
            ), 409
        cursor.execute(
            """
            INSERT INTO Team_Memberships (
                team_id, player_id, membership_from, membership_to
            )
            VALUES (%s, %s, %s, %s)
            """,
            (team_id, player_id, membership_from, membership_to),
        )
    return jsonify(
        membership={
            "team_id": team_id,
            "player_id": player_id,
            "membership_from": membership_from,
            "membership_to": membership_to,
        }
    ), 201


@management_api.delete("/teams/<int:team_id>/members/<int:player_id>")
def end_team_membership(team_id, player_id):
    end_date = date.today()
    with transaction() as cursor:
        cursor.execute(
            """
            SELECT membership_from
            FROM Team_Memberships
            WHERE team_id = %s AND player_id = %s
              AND membership_from <= %s
              AND (membership_to IS NULL OR membership_to >= %s)
            ORDER BY membership_from DESC
            LIMIT 1 FOR UPDATE
            """,
            (team_id, player_id, end_date, end_date),
        )
        membership = cursor.fetchone()
        if membership is None:
            return jsonify(error="Active team membership not found."), 404
        start = membership["membership_from"]
        closed_on = max(start, end_date)
        cursor.execute(
            """
            UPDATE Team_Memberships SET membership_to = %s
            WHERE team_id = %s AND player_id = %s AND membership_from = %s
            """,
            (closed_on, team_id, player_id, start),
        )
    return jsonify(
        message="Team membership ended.",
        team_id=team_id,
        player_id=player_id,
        membership_to=closed_on.isoformat(),
    )


def _tournament_values(data, *, partial=False):
    values = {}
    required = ("sport_id", "name", "competition_format", "season", "start_date", "end_date")
    if not partial:
        missing = [field for field in required if field not in data]
        if missing:
            return None, "Missing required field(s): " + ", ".join(missing)
    if "sport_id" in data:
        values["sport_id"], error = _required_id(data, "sport_id")
        if error:
            return None, error
    for field, maximum in (("name", 150), ("season", 40)):
        if field in data:
            values[field], error = _bounded_text(data, field, maximum, required=True)
            if error:
                return None, error
    if "competition_format" in data:
        value = data["competition_format"]
        if not isinstance(value, str) or value not in TOURNAMENT_FORMATS:
            return None, "competition_format must be 'team' or 'individual'."
        values["competition_format"] = value
    for field in ("start_date", "end_date"):
        if field in data:
            values[field], error = _optional_date(data, field, required=True)
            if error:
                return None, error
    if "status" in data:
        value = data["status"]
        if not isinstance(value, str) or value not in TOURNAMENT_STATUSES:
            return None, "status is not a supported tournament status."
        values["status"] = value
    if "is_published" in data:
        values["is_published"], error = _boolean(data, "is_published")
        if error:
            return None, error
    if "description" in data:
        value = data["description"]
        if value is not None and not isinstance(value, str):
            return None, "description must be a string or null."
        values["description"] = value
    if "scoring_rules" in data:
        rules = data["scoring_rules"]
        if rules is not None and not isinstance(rules, dict):
            return None, "scoring_rules must be an object."
        if rules is not None:
            parsed_rules = {}
            for key, default in (
                ("points_for_win", Decimal("3.00")),
                ("points_for_draw", Decimal("1.00")),
                ("points_for_loss", Decimal("0.00")),
            ):
                parsed_rules[key], error = _decimal(rules, key, default)
                if error:
                    return None, error
            values["scoring_rules"] = parsed_rules
    if "start_date" in values and "end_date" in values:
        if values["end_date"] < values["start_date"]:
            return None, "end_date must be on or after start_date."
    return values, None


def _write_scoring_rules(cursor, tournament_id, rules):
    cursor.execute(
        """
        INSERT INTO Tournament_Scoring_Rules (
            tournament_id, points_for_win, points_for_draw, points_for_loss
        )
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            points_for_win = VALUES(points_for_win),
            points_for_draw = VALUES(points_for_draw),
            points_for_loss = VALUES(points_for_loss)
        """,
        (
            tournament_id,
            rules["points_for_win"],
            rules["points_for_draw"],
            rules["points_for_loss"],
        ),
    )


def _tournament_details(tournament_id, include_all=True):
    if include_all:
        return fetch_one(
            """
            SELECT t.tournament_id, t.name AS tournament_name, t.sport_id,
                   sp.name AS sport_name, t.competition_format, t.season,
                   t.start_date, t.end_date, t.status AS tournament_status,
                   t.is_published, t.description,
                   rules.points_for_win, rules.points_for_draw,
                   rules.points_for_loss
            FROM Tournaments t
            JOIN Sports sp ON sp.sport_id = t.sport_id
            LEFT JOIN Tournament_Scoring_Rules rules
                ON rules.tournament_id = t.tournament_id
            WHERE t.tournament_id = %s
            """,
            (tournament_id,),
        )
    return fetch_one(
        """
        SELECT tournament_id, tournament_name, sport_id, sport_name,
               competition_format, season, start_date, end_date,
               tournament_status, description
        FROM vw_published_tournaments
        WHERE tournament_id = %s
        """,
        (tournament_id,),
    )


@management_api.post("/tournaments")
def create_tournament():
    data = _json_object()
    if data is None:
        if request.get_data(cache=True):
            return jsonify(error="A JSON object is required."), 400
        return jsonify(error="A JSON object is required."), 400
    values, error = _tournament_values(data)
    if error:
        return jsonify(error=error), 400
    values.setdefault("status", "planned")
    values.setdefault("is_published", False)
    values.setdefault("description", None)
    with transaction() as cursor:
        cursor.execute(
            "SELECT sport_id FROM Sports WHERE sport_id = %s FOR UPDATE",
            (values["sport_id"],),
        )
        if cursor.fetchone() is None:
            return jsonify(error="Sport not found."), 404
        cursor.execute(
            """
            INSERT INTO Tournaments (
                sport_id, name, competition_format, season, start_date,
                end_date, status, is_published, description
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                values["sport_id"],
                values["name"],
                values["competition_format"],
                values["season"],
                values["start_date"],
                values["end_date"],
                values["status"],
                values["is_published"],
                values["description"],
            ),
        )
        tournament_id = cursor.lastrowid
        if values.get("scoring_rules") is not None:
            _write_scoring_rules(cursor, tournament_id, values["scoring_rules"])
    return jsonify(tournament={"tournament_id": tournament_id, **values}), 201


@management_api.put("/tournaments/<int:tournament_id>")
def update_tournament(tournament_id):
    data = _json_object()
    if data is None:
        return jsonify(error="A JSON object is required."), 400
    if "status" in data:
        return jsonify(
            error="Use PATCH /api/tournaments/<id>/status to change tournament status."
        ), 400
    values, error = _tournament_values(data, partial=True)
    if error:
        return jsonify(error=error), 400
    scoring_rules = values.pop("scoring_rules", None)
    if not values and scoring_rules is None:
        return jsonify(error="At least one updatable field is required."), 400
    sensitive_fields = {"sport_id", "competition_format", "start_date", "end_date"}
    with transaction() as cursor:
        cursor.execute(
            """
            SELECT tournament_id, start_date, end_date
            FROM Tournaments WHERE tournament_id = %s FOR UPDATE
            """,
            (tournament_id,),
        )
        existing = cursor.fetchone()
        if existing is None:
            return jsonify(error="Tournament not found."), 404
        if "sport_id" in values:
            cursor.execute("SELECT sport_id FROM Sports WHERE sport_id = %s", (values["sport_id"],))
            if cursor.fetchone() is None:
                return jsonify(error="Sport not found."), 404
        if sensitive_fields.intersection(values):
            cursor.execute(
                """
                SELECT
                    EXISTS(SELECT 1 FROM Tournament_Entries WHERE tournament_id = %s)
                    OR EXISTS(SELECT 1 FROM Matches WHERE tournament_id = %s)
                    AS has_history
                """,
                (tournament_id, tournament_id),
            )
            if cursor.fetchone()["has_history"]:
                return jsonify(
                    error="Sport, format, and tournament dates cannot change after entries or matches exist."
                ), 409
        start_date = (
            date.fromisoformat(values["start_date"])
            if "start_date" in values
            else existing["start_date"]
        )
        end_date = (
            date.fromisoformat(values["end_date"])
            if "end_date" in values
            else existing["end_date"]
        )
        if end_date < start_date:
            return jsonify(error="end_date must be on or after start_date."), 400
        update_values = {key: value for key, value in values.items()}
        if update_values:
            columns = ", ".join(f"{key} = %s" for key in update_values)
            cursor.execute(
                f"UPDATE Tournaments SET {columns} WHERE tournament_id = %s",
                (*update_values.values(), tournament_id),
            )
        if scoring_rules is not None:
            _write_scoring_rules(cursor, tournament_id, scoring_rules)
    return jsonify(tournament=_tournament_details(tournament_id))


@management_api.patch("/tournaments/<int:tournament_id>/status")
def update_tournament_status(tournament_id):
    data = _json_object()
    if data is None:
        return jsonify(error="A JSON object is required."), 400
    status = data.get("status")
    if not isinstance(status, str) or status not in TOURNAMENT_STATUSES:
        return jsonify(error="status is not a supported tournament status."), 400
    if status == "cancelled":
        return cancel_tournament(tournament_id)
    with transaction() as cursor:
        cursor.execute(
            "SELECT tournament_id, status FROM Tournaments WHERE tournament_id = %s FOR UPDATE",
            (tournament_id,),
        )
        tournament = cursor.fetchone()
        if tournament is None:
            return jsonify(error="Tournament not found."), 404
        if tournament["status"] == "cancelled":
            return jsonify(error="A cancelled tournament cannot be reopened."), 409
        cursor.execute(
            "UPDATE Tournaments SET status = %s WHERE tournament_id = %s",
            (status, tournament_id),
        )
    return jsonify(tournament=_tournament_details(tournament_id))


@management_api.post("/tournaments/<int:tournament_id>/cancel")
def cancel_tournament(tournament_id):
    with transaction() as cursor:
        cursor.execute(
            """
            SELECT t.status,
                   EXISTS(
                       SELECT 1 FROM Matches m
                       WHERE m.tournament_id = t.tournament_id
                         AND m.status IN ('completed', 'live')
                   ) AS has_active_or_completed_matches
            FROM Tournaments t
            WHERE t.tournament_id = %s
            FOR UPDATE
            """,
            (tournament_id,),
        )
        tournament = cursor.fetchone()
        if tournament is None:
            return jsonify(error="Tournament not found."), 404
        if tournament["has_active_or_completed_matches"]:
            return jsonify(
                error="A tournament with live or completed matches cannot be cancelled."
            ), 409
        cursor.execute(
            """
            UPDATE Matches SET status = 'cancelled'
            WHERE tournament_id = %s AND status IN ('scheduled', 'postponed')
            """,
            (tournament_id,),
        )
        cursor.execute(
            "UPDATE Tournaments SET status = 'cancelled' WHERE tournament_id = %s",
            (tournament_id,),
        )
    return jsonify(tournament=_tournament_details(tournament_id))


@management_api.get("/tournaments/<int:tournament_id>/registrations")
def list_tournament_registrations(tournament_id):
    include_unpublished = request.args.get("include_unpublished", "").lower()
    if include_unpublished not in ("", "true", "false"):
        return jsonify(error="include_unpublished must be true or false."), 400
    if include_unpublished == "true":
        tournament = fetch_one(
            "SELECT tournament_id FROM Tournaments WHERE tournament_id = %s",
            (tournament_id,),
        )
        entries = fetch_all(
            """
        SELECT te.entry_id, te.tournament_id, te.team_id, team.name AS team_name,
               team.team_code, te.status AS entry_status, te.registered_at
        FROM Tournament_Entries te
        JOIN Teams team ON team.team_id = te.team_id
        WHERE te.tournament_id = %s
        ORDER BY te.registered_at, te.entry_id
        """,
            (tournament_id,),
        )
    else:
        tournament = fetch_one(
            """
            SELECT tournament_id
            FROM vw_published_tournaments
            WHERE tournament_id = %s
            """,
            (tournament_id,),
        )
        entries = fetch_all(
            """
            SELECT participant.entry_id, participant.tournament_id,
                   participant.team_id, participant.team_name, team.team_code,
                   participant.entry_status, participant.registered_at
            FROM vw_tournament_participants participant
            JOIN Tournament_Entries te ON te.entry_id = participant.entry_id
            JOIN Teams team ON team.team_id = participant.team_id
            WHERE participant.tournament_id = %s
              AND participant.team_id IS NOT NULL
            ORDER BY participant.registered_at, participant.entry_id
            """,
            (tournament_id,),
        )
    if tournament is None:
        return jsonify(error="Tournament not found."), 404
    return jsonify(tournament_id=tournament_id, items=entries)


@management_api.post("/tournaments/<int:tournament_id>/teams")
def register_tournament_team(tournament_id):
    data = _json_object()
    if data is None:
        return jsonify(error="A JSON object is required."), 400
    team_id, error = _required_id(data, "team_id")
    if error:
        return jsonify(error=error), 400
    with transaction() as cursor:
        cursor.execute(
            """
            SELECT tournament_id, sport_id, competition_format, status,
                   start_date
            FROM Tournaments
            WHERE tournament_id = %s
            FOR UPDATE
            """,
            (tournament_id,),
        )
        tournament = cursor.fetchone()
        if tournament is None:
            return jsonify(error="Tournament not found."), 404
        if tournament["competition_format"] != "team":
            return jsonify(error="Only team-format tournaments accept team registrations."), 409
        if tournament["status"] != "registration":
            return jsonify(error="Tournament is not open for registration."), 409
        if tournament["start_date"] <= date.today():
            return jsonify(
                error="Registration is closed on or after the tournament start date."
            ), 409
        cursor.execute(
            "SELECT team_id, sport_id, is_active FROM Teams WHERE team_id = %s FOR UPDATE",
            (team_id,),
        )
        team = cursor.fetchone()
        if team is None:
            return jsonify(error="Team not found."), 404
        if not team["is_active"]:
            return jsonify(error="Inactive teams cannot be registered."), 409
        if team["sport_id"] != tournament["sport_id"]:
            return jsonify(error="Team sport must match tournament sport."), 400
        cursor.execute(
            """
            SELECT entry_id, status
            FROM Tournament_Entries
            WHERE tournament_id = %s AND team_id = %s
            """,
            (tournament_id, team_id),
        )
        if cursor.fetchone() is not None:
            return jsonify(error="This team already has a tournament entry."), 409
        cursor.execute(
            """
            INSERT INTO Tournament_Entries (tournament_id, team_id, status)
            VALUES (%s, %s, 'registered')
            """,
            (tournament_id, team_id),
        )
        entry_id = cursor.lastrowid
    return jsonify(
        entry={
            "entry_id": entry_id,
            "tournament_id": tournament_id,
            "team_id": team_id,
            "entry_status": "registered",
        }
    ), 201


@management_api.post("/matches")
def create_match():
    data = _json_object()
    if data is None:
        return jsonify(error="A JSON object is required."), 400
    tournament_id, error = _required_id(data, "tournament_id")
    if error:
        return jsonify(error=error), 400
    match_number, error = _required_id(data, "match_number")
    if error:
        return jsonify(error=error), 400
    entry_ids, error = _participant_ids(data)
    if error:
        return jsonify(error=error), 400
    scheduled_at, error = _optional_datetime(data, "scheduled_at")
    if error:
        return jsonify(error=error), 400
    stage, error = _bounded_text(data, "stage", 60)
    if error:
        return jsonify(error=error), 400
    round_name, error = _bounded_text(data, "round_name", 100)
    if error:
        return jsonify(error=error), 400
    venue, error = _bounded_text(data, "venue", 200)
    if error:
        return jsonify(error=error), 400
    with transaction() as cursor:
        cursor.execute(
            """
            SELECT tournament_id, competition_format, status
            FROM Tournaments WHERE tournament_id = %s FOR UPDATE
            """,
            (tournament_id,),
        )
        tournament = cursor.fetchone()
        if tournament is None:
            return jsonify(error="Tournament not found."), 404
        if tournament["status"] in ("cancelled", "completed"):
            return jsonify(error="Matches cannot be added to a cancelled or completed tournament."), 409
        if tournament["competition_format"] == "team" and len(entry_ids) != 2:
            return jsonify(error="Team matches require exactly two participants."), 400
        participants = _participant_rows(cursor, tournament_id, entry_ids)
        if len(participants) != len(entry_ids):
            return jsonify(
                error="Every match entry must belong to this tournament."
            ), 400
        if any(participant["status"] != "registered" for participant in participants):
            return jsonify(error="Withdrawn or disqualified entries cannot be scheduled."), 409
        if tournament["competition_format"] == "team" and any(
            row["team_id"] is None for row in participants
        ):
            return jsonify(error="Team tournaments require team entries."), 400
        if tournament["competition_format"] == "individual" and any(
            row["player_id"] is None for row in participants
        ):
            return jsonify(error="Individual tournaments require player entries."), 400
        conflict = _check_team_schedule_conflict(cursor, entry_ids, scheduled_at)
        if conflict:
            return jsonify(error="A participating team already has a match at this exact time."), 409
        cursor.execute(
            """
            INSERT INTO Matches (
                tournament_id, match_number, stage, round_name,
                scheduled_at, venue, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'scheduled')
            """,
            (tournament_id, match_number, stage, round_name, scheduled_at, venue),
        )
        match_id = cursor.lastrowid
        for entry_id in entry_ids:
            cursor.execute(
                "INSERT INTO Match_Entries (match_id, entry_id) VALUES (%s, %s)",
                (match_id, entry_id),
            )
    return jsonify(
        match={
            "match_id": match_id,
            "tournament_id": tournament_id,
            "match_number": match_number,
            "stage": stage,
            "round_name": round_name,
            "scheduled_at": scheduled_at,
            "venue": venue,
            "match_status": "scheduled",
            "entry_ids": entry_ids,
        }
    ), 201


@management_api.put("/matches/<int:match_id>")
def update_match(match_id):
    data = _json_object()
    if data is None:
        return jsonify(error="A JSON object is required."), 400
    values = {}
    if "scheduled_at" in data:
        values["scheduled_at"], error = _optional_datetime(data, "scheduled_at")
        if error:
            return jsonify(error=error), 400
    for field, maximum in (("stage", 60), ("round_name", 100), ("venue", 200)):
        if field in data:
            values[field], error = _bounded_text(data, field, maximum)
            if error:
                return jsonify(error=error), 400
    if "status" in data:
        status = data["status"]
        if not isinstance(status, str) or status not in MATCH_STATUSES:
            return jsonify(error="status is not a supported match status."), 400
        if status == "completed":
            return jsonify(
                error="Use the results endpoint to declare results and complete a match."
            ), 400
        values["status"] = status
    if not values:
        return jsonify(error="At least one schedule, venue, or status field is required."), 400
    with transaction() as cursor:
        cursor.execute(
            "SELECT match_id, status FROM Matches WHERE match_id = %s FOR UPDATE",
            (match_id,),
        )
        match = cursor.fetchone()
        if match is None:
            return jsonify(error="Match not found."), 404
        if match["status"] == "completed" and (
            "scheduled_at" in values or values.get("status") != "completed"
        ):
            return jsonify(error="Completed match schedules and status cannot be changed."), 409
        cursor.execute(
            "SELECT entry_id FROM Match_Entries WHERE match_id = %s ORDER BY entry_id",
            (match_id,),
        )
        entry_ids = [row["entry_id"] for row in cursor.fetchall()]
        scheduled_at = values.get("scheduled_at")
        if "scheduled_at" in values and values["scheduled_at"] is None:
            scheduled_at = None
        elif "scheduled_at" not in values:
            cursor.execute(
                "SELECT scheduled_at FROM Matches WHERE match_id = %s",
                (match_id,),
            )
            scheduled_at = cursor.fetchone()["scheduled_at"]
        target_status = values.get("status", match["status"])
        conflict = (
            _check_team_schedule_conflict(
                cursor, entry_ids, scheduled_at, exclude_match_id=match_id
            )
            if entry_ids and target_status in ("scheduled", "live")
            else None
        )
        if conflict:
            return jsonify(error="A participating team already has a match at this exact time."), 409
        columns = ", ".join(f"{key} = %s" for key in values)
        cursor.execute(
            f"UPDATE Matches SET {columns} WHERE match_id = %s",
            (*values.values(), match_id),
        )
    return jsonify(match={"match_id": match_id, **values})


@management_api.patch("/matches/<int:match_id>/status")
def update_match_status(match_id):
    data = _json_object()
    if data is None:
        return jsonify(error="A JSON object is required."), 400
    status = data.get("status")
    if status == "completed":
        return jsonify(
            error="Use the results endpoint to declare results and complete a match."
        ), 400
    if not isinstance(status, str) or status not in MATCH_STATUSES:
        return jsonify(error="status is not a supported match status."), 400
    with transaction() as cursor:
        cursor.execute(
            """
            SELECT status, scheduled_at
            FROM Matches WHERE match_id = %s FOR UPDATE
            """,
            (match_id,),
        )
        match = cursor.fetchone()
        if match is None:
            return jsonify(error="Match not found."), 404
        if match["status"] == "completed":
            return jsonify(error="Completed match status cannot be changed."), 409
        if status in ("scheduled", "live"):
            cursor.execute(
                "SELECT entry_id FROM Match_Entries WHERE match_id = %s",
                (match_id,),
            )
            entry_ids = [row["entry_id"] for row in cursor.fetchall()]
            conflict = _check_team_schedule_conflict(
                cursor, entry_ids, match["scheduled_at"], exclude_match_id=match_id
            ) if entry_ids else None
            if conflict:
                return jsonify(
                    error="A participating team already has a match at this exact time."
                ), 409
        cursor.execute(
            "UPDATE Matches SET status = %s WHERE match_id = %s",
            (status, match_id),
        )
    return jsonify(match={"match_id": match_id, "match_status": status})


@management_api.get("/matches/<int:match_id>/participants")
def match_participants(match_id):
    include_unpublished = request.args.get("include_unpublished", "").lower()
    if include_unpublished not in ("", "true", "false"):
        return jsonify(error="include_unpublished must be true or false."), 400
    if include_unpublished == "true":
        match = fetch_one(
            """
            SELECT match_id, status AS match_status
            FROM Matches
            WHERE match_id = %s
            """,
            (match_id,),
        )
    else:
        match = fetch_one(
            """
            SELECT schedule.match_id, schedule.match_status
            FROM vw_match_schedule schedule
            WHERE schedule.match_id = %s
            """,
            (match_id,),
        )
    if match is None:
        return jsonify(error="Match not found."), 404
    participants = fetch_all(
        """
        SELECT me.entry_id, te.team_id, team.name AS team_name,
               te.player_id,
               CONCAT_WS(' ', student.first_name, student.last_name) AS player_name,
               result_row.outcome, result_row.result_rank, result_row.official_note
        FROM Match_Entries me
        JOIN Tournament_Entries te ON te.entry_id = me.entry_id
        LEFT JOIN Teams team ON team.team_id = te.team_id
        LEFT JOIN Players player ON player.player_id = te.player_id
        LEFT JOIN Students student ON student.student_id = player.student_id
        LEFT JOIN Match_Results result_row
          ON result_row.match_id = me.match_id
         AND result_row.entry_id = me.entry_id
        JOIN Matches match_row ON match_row.match_id = me.match_id
        JOIN Tournaments tournament
          ON tournament.tournament_id = match_row.tournament_id
        JOIN Sports sport ON sport.sport_id = tournament.sport_id
        WHERE me.match_id = %s
          AND (
              %s = TRUE
              OR (
                  tournament.is_published = TRUE
                  AND sport.is_active = TRUE
              )
          )
        ORDER BY me.entry_id
        """,
        (match_id, include_unpublished == "true"),
    )
    scores = fetch_all(
        """
        SELECT entry_id, segment_number, segment_label, numeric_value, text_value
        FROM Match_Scores score
        JOIN Matches match_row ON match_row.match_id = score.match_id
        JOIN Tournaments tournament
          ON tournament.tournament_id = match_row.tournament_id
        JOIN Sports sport ON sport.sport_id = tournament.sport_id
        WHERE score.match_id = %s
          AND (
              %s = TRUE
              OR (
                  tournament.is_published = TRUE
                  AND sport.is_active = TRUE
              )
          )
        ORDER BY entry_id, segment_number
        """,
        (match_id, include_unpublished == "true"),
    )
    scores_by_entry = {}
    for score in scores:
        scores_by_entry.setdefault(score["entry_id"], []).append(
            {
                "segment_number": score["segment_number"],
                "segment_label": score["segment_label"],
                "numeric_value": score["numeric_value"],
                "text_value": score["text_value"],
            }
        )
    team_ids = sorted({participant["team_id"] for participant in participants if participant["team_id"]})
    roster_by_team = {team_id: [] for team_id in team_ids}
    if team_ids:
        placeholders = ", ".join(["%s"] * len(team_ids))
        roster_rows = fetch_all(
            f"""
            SELECT tm.team_id,
                   CONCAT_WS(' ', student.first_name, student.last_name) AS player_name
            FROM Team_Memberships tm
            JOIN Players player ON player.player_id = tm.player_id
            JOIN Students student ON student.student_id = player.student_id
            WHERE tm.team_id IN ({placeholders})
              AND tm.membership_to IS NULL
            ORDER BY tm.team_id, student.first_name, student.last_name
            """,
            tuple(team_ids),
        )
        for roster_row in roster_rows:
            roster_by_team[roster_row["team_id"]].append(roster_row["player_name"])
    for participant in participants:
        participant["scores"] = scores_by_entry.get(participant["entry_id"], [])
        participant["roster_players"] = roster_by_team.get(participant["team_id"], [])
    return jsonify(match=match, participants=participants)


@management_api.put("/matches/<int:match_id>/scores")
def save_match_scores(match_id):
    data = _json_object()
    if data is None:
        return jsonify(error="A JSON object is required."), 400
    with transaction() as cursor:
        cursor.execute(
            """
            SELECT m.match_id, m.status
            FROM Matches m WHERE m.match_id = %s FOR UPDATE
            """,
            (match_id,),
        )
        match = cursor.fetchone()
        if match is None:
            return jsonify(error="Match not found."), 404
        if match["status"] in ("completed", "cancelled"):
            return jsonify(error="Scores cannot be changed for a completed or cancelled match."), 409
        cursor.execute(
            "SELECT entry_id FROM Match_Entries WHERE match_id = %s FOR UPDATE",
            (match_id,),
        )
        participant_ids = {row["entry_id"] for row in cursor.fetchall()}
        if len(participant_ids) < 2:
            return jsonify(error="The match needs at least two participants before scoring."), 409
        scores, error = _validated_score_rows(data.get("scores"), participant_ids)
        if error:
            return jsonify(error=error), 400
        if not scores:
            return jsonify(error="scores must contain at least one score segment."), 400
        _save_scores(cursor, match_id, scores)
    return jsonify(match_id=match_id, scores_saved=len(scores))


@management_api.put("/matches/<int:match_id>/results")
def declare_match_results(match_id):
    data = _json_object()
    if data is None:
        return jsonify(error="A JSON object is required."), 400
    results = data.get("results")
    if not isinstance(results, list) or not results:
        return jsonify(error="results must be a non-empty array."), 400
    with transaction() as cursor:
        cursor.execute(
            """
            SELECT m.match_id, m.status, t.competition_format
            FROM Matches m JOIN Tournaments t ON t.tournament_id = m.tournament_id
            WHERE m.match_id = %s FOR UPDATE
            """,
            (match_id,),
        )
        match = cursor.fetchone()
        if match is None:
            return jsonify(error="Match not found."), 404
        if match["status"] == "cancelled":
            return jsonify(error="Cancelled matches cannot be completed."), 409
        cursor.execute(
            "SELECT entry_id FROM Match_Entries WHERE match_id = %s ORDER BY entry_id FOR UPDATE",
            (match_id,),
        )
        participant_ids = [row["entry_id"] for row in cursor.fetchall()]
        if len(participant_ids) < 2:
            return jsonify(error="The match needs at least two participants."), 409
        parsed_results = []
        seen = set()
        for index, result in enumerate(results):
            if not isinstance(result, dict):
                return jsonify(error=f"results[{index}] must be an object."), 400
            entry_id = _positive_id(result.get("entry_id"))
            if entry_id is None or entry_id not in participant_ids:
                return jsonify(error=f"results[{index}].entry_id must be a match participant."), 400
            if entry_id in seen:
                return jsonify(error="Each match participant may have only one result."), 400
            seen.add(entry_id)
            outcome = result.get("outcome")
            if not isinstance(outcome, str) or outcome.strip().lower() not in RESULT_OUTCOMES:
                return jsonify(error=f"results[{index}].outcome is not supported."), 400
            outcome = outcome.strip().lower()
            rank = result.get("result_rank")
            if rank is not None:
                rank = _positive_id(rank)
                if rank is None:
                    return jsonify(error=f"results[{index}].result_rank must be positive or null."), 400
            note = result.get("official_note")
            if note is not None and not isinstance(note, str):
                return jsonify(error=f"results[{index}].official_note must be a string or null."), 400
            parsed_results.append((entry_id, outcome, rank, note))
        if seen != set(participant_ids):
            return jsonify(error="A result is required for every match participant."), 400
        outcomes = [result[1] for result in parsed_results]
        if match["competition_format"] == "team":
            if len(participant_ids) != 2:
                return jsonify(error="Team matches require exactly two participants."), 409
            if not (outcomes.count("draw") == 2 or (outcomes.count("win") == 1 and outcomes.count("loss") == 1)):
                return jsonify(error="Team results must be one win and one loss, or two draws."), 400
        elif "draw" in outcomes and outcomes.count("draw") != len(outcomes):
            return jsonify(error="Individual match draws must apply to every participant."), 400
        scores = []
        if "scores" in data:
            scores, error = _validated_score_rows(data["scores"], set(participant_ids))
            if error:
                return jsonify(error=error), 400
        for entry_id, outcome, rank, note in parsed_results:
            cursor.execute(
                """
                INSERT INTO Match_Results (
                    match_id, entry_id, outcome, result_rank, official_note
                )
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    outcome = VALUES(outcome),
                    result_rank = VALUES(result_rank),
                    official_note = VALUES(official_note),
                    declared_at = CURRENT_TIMESTAMP
                """,
                (match_id, entry_id, outcome, rank, note),
            )
        if scores:
            _save_scores(cursor, match_id, scores)
        cursor.execute(
            "UPDATE Matches SET status = 'completed' WHERE match_id = %s",
            (match_id,),
        )
    return jsonify(
        match_id=match_id,
        match_status="completed",
        results_saved=len(parsed_results),
        scores_saved=len(scores),
    )


@management_api.get("/reports/summary")
def report_summary():
    summary = fetch_one(
        """
        SELECT
            (SELECT COUNT(*) FROM Students) AS total_students,
            (SELECT COUNT(*) FROM Players) AS total_players,
            (SELECT COUNT(*) FROM Teams) AS total_teams,
            (SELECT COUNT(*) FROM Tournaments) AS total_tournaments,
            (SELECT COUNT(*) FROM Tournaments WHERE is_published = TRUE)
                AS published_tournaments,
            (SELECT COUNT(*) FROM Tournament_Entries
             WHERE status = 'registered') AS tournament_participants,
            (SELECT COUNT(*) FROM Matches) AS total_matches,
            (SELECT COUNT(*) FROM Match_Results) AS total_match_results,
            (SELECT COUNT(*) FROM Match_Results result_row
             JOIN Matches m ON m.match_id = result_row.match_id
             WHERE m.status = 'completed' AND result_row.outcome = 'win')
                AS completed_match_wins
        """
    )
    return jsonify(summary=summary)


@management_api.get("/reports/tournaments/<int:tournament_id>")
def tournament_report(tournament_id):
    include_unpublished = request.args.get("include_unpublished", "").lower()
    if include_unpublished not in ("", "true", "false"):
        return jsonify(error="include_unpublished must be true or false."), 400
    if include_unpublished != "true":
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
    result_sets = fetch_procedure_result_sets(
        "CALL sp_get_tournament_report(%s)",
        (tournament_id,),
    )
    if not result_sets or not result_sets[0]:
        return jsonify(error="Tournament not found."), 404
    return jsonify(
        tournament=result_sets[0][0],
        result_summary=result_sets[1] if len(result_sets) > 1 else [],
    )


@management_api.get("/reports/match-results")
def report_match_results():
    tournament_id = request.args.get("tournament_id")
    include_unpublished = request.args.get("include_unpublished", "").lower() == "true"
    if tournament_id is not None:
        tournament_id = _positive_id(tournament_id)
        if tournament_id is None:
            return jsonify(error="tournament_id must be a positive integer."), 400
    clauses = ["m.status = 'completed'"]
    params = []
    if not include_unpublished:
        clauses.extend(["t.is_published = TRUE", "sp.is_active = TRUE"])
    if tournament_id is not None:
        clauses.append("m.tournament_id = %s")
        params.append(tournament_id)
    rows = fetch_all(
        f"""
        SELECT m.match_id, m.tournament_id, t.name AS tournament_name,
               m.match_number, me.entry_id,
               CASE WHEN te.team_id IS NOT NULL THEN 'team' ELSE 'individual' END
                   AS participant_type,
               te.team_id, team.name AS team_name, te.player_id,
               CONCAT_WS(' ', s.first_name, s.last_name) AS player_name,
               result_row.outcome, result_row.result_rank,
               result_row.official_note, result_row.declared_at
        FROM Matches m
        JOIN Tournaments t ON t.tournament_id = m.tournament_id
        JOIN Sports sp ON sp.sport_id = t.sport_id
        JOIN Match_Entries me ON me.match_id = m.match_id
        JOIN Tournament_Entries te ON te.entry_id = me.entry_id
        JOIN Match_Results result_row
          ON result_row.match_id = me.match_id
         AND result_row.entry_id = me.entry_id
        LEFT JOIN Teams team ON team.team_id = te.team_id
        LEFT JOIN Players p ON p.player_id = te.player_id
        LEFT JOIN Students s ON s.student_id = p.student_id
        WHERE {' AND '.join(clauses)}
        ORDER BY m.tournament_id, m.match_number, me.entry_id
        """,
        tuple(params),
    )
    return jsonify(items=rows)


@management_api.get("/reports/tournament-winners")
def report_tournament_winners():
    rows = fetch_all(
        """
        SELECT standings.tournament_id, standings.tournament_name,
               standings.season, sp.name AS sport_name, t.is_published,
               standings.entry_id, standings.team_id, standings.team_name,
               standings.player_id, standings.player_name,
               standings.standings_rank, standings.total_points,
               standings.best_result_rank
        FROM vw_tournament_standings standings
        JOIN Tournaments t ON t.tournament_id = standings.tournament_id
        JOIN Sports sp ON sp.sport_id = t.sport_id
        WHERE t.status = 'completed'
          AND standings.standings_rank = 1
          AND (
              standings.competition_format = 'team'
              OR standings.best_result_rank IS NOT NULL
          )
        ORDER BY t.start_date DESC, standings.entry_id
        """
    )
    return jsonify(items=rows)
