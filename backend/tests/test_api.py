import unittest
from unittest.mock import patch

from app import create_app
from app.db import DatabaseConfigurationError


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True})
        self.client = self.app.test_client()

    @patch("app.api.fetch_one", return_value={"database_connected": 1})
    def test_health_checks_database(self, fetch_one):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["database"], "connected")
        fetch_one.assert_called_once_with("SELECT 1 AS database_connected")

    @patch("app.db.get_connection", side_effect=DatabaseConfigurationError("missing config"))
    def test_health_returns_sanitized_unavailable_response(self, get_connection):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.get_json()["error"],
            "Database configuration is unavailable.",
        )

    @patch("app.api.fetch_one")
    @patch("app.api.execute", return_value=42)
    def test_create_student_is_open_and_uses_validated_parameters(
        self, execute, fetch_one
    ):
        fetch_one.return_value = {
            "student_id": 42,
            "student_number": "STU-42",
            "first_name": "Test",
            "last_name": "Student",
            "email": None,
            "department_id": None,
            "department_name": None,
            "enrollment_status": "active",
            "created_at": None,
        }
        response = self.client.post(
            "/api/students",
            json={
                "student_number": "STU-42",
                "first_name": " Test ",
                "last_name": "Student",
                "enrollment_status": "active",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["student"]["student_id"], 42)
        self.assertEqual(
            execute.call_args.args[1],
            ("STU-42", "Test", "Student", None, None, "active"),
        )

    @patch("app.api.fetch_all", return_value=[])
    def test_public_tournaments_use_published_view(self, fetch_all):
        response = self.client.get("/api/tournaments")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["items"], [])
        self.assertIn("vw_published_tournaments", fetch_all.call_args.args[0])

    @patch("app.api.fetch_procedure_rows", return_value=[])
    @patch("app.api.fetch_one", return_value={"tournament_id": 4})
    def test_standings_use_existing_procedure(self, fetch_one, fetch_procedure_rows):
        response = self.client.get("/api/tournaments/4/standings")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["standings"], [])
        fetch_procedure_rows.assert_called_once_with(
            "CALL sp_get_tournament_standings(%s)",
            (4,),
        )

    def test_all_application_routes_are_registered_without_auth_routes(self):
        routes = {
            rule.rule
            for rule in self.app.url_map.iter_rules()
            if rule.rule.startswith("/api/")
        }
        expected = {
            "/api/health",
            "/api/dashboard/stats",
            "/api/students",
            "/api/students/<int:student_id>",
            "/api/sports",
            "/api/departments",
            "/api/teams",
            "/api/tournaments",
            "/api/tournaments/<int:tournament_id>",
            "/api/matches",
            "/api/matches/<int:match_id>",
            "/api/matches/<int:match_id>/results",
            "/api/matches/<int:match_id>/participants",
            "/api/tournaments/<int:tournament_id>/standings",
            "/api/sports/<int:sport_id>",
            "/api/players",
            "/api/players/<int:player_id>",
            "/api/students/<int:student_id>/player",
            "/api/players/<int:player_id>/eligibility",
            "/api/players/<int:player_id>/eligibility/<int:sport_id>",
            "/api/teams/<int:team_id>",
            "/api/teams/<int:team_id>/members",
            "/api/teams/<int:team_id>/members/<int:player_id>",
            "/api/tournaments/<int:tournament_id>/status",
            "/api/tournaments/<int:tournament_id>/cancel",
            "/api/tournaments/<int:tournament_id>/registrations",
            "/api/tournaments/<int:tournament_id>/teams",
            "/api/matches/<int:match_id>/status",
            "/api/matches/<int:match_id>/scores",
            "/api/matches/<int:match_id>/results",
            "/api/reports/summary",
            "/api/reports/tournaments/<int:tournament_id>",
            "/api/reports/match-results",
            "/api/reports/tournament-winners",
        }
        self.assertTrue(expected.issubset(routes))

    def test_student_validation_runs_without_login(self):
        response = self.client.post(
            "/api/students",
            json={"student_number": "STU-42"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing required field", response.get_json()["error"])

    @patch("app.api.fetch_one", return_value={"students": 12})
    def test_dashboard_is_open_without_bearer_token(self, fetch_one):
        response = self.client.get("/api/dashboard/stats")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["stats"]["students"], 12)
        fetch_one.assert_called_once()

    @patch("app.api.fetch_one", return_value={"total": 0})
    @patch("app.api.fetch_all", return_value=[])
    def test_student_list_accepts_filters(self, fetch_all, fetch_one):
        response = self.client.get(
            "/api/students?page=2&per_page=5&has_player=true&sport_id=3"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["items"], [])
        self.assertEqual(fetch_all.call_args.args[1][-3:], (3, 5, 5))

    def test_invalid_student_filter_is_rejected(self):
        response = self.client.get("/api/students?has_player=yes")
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
