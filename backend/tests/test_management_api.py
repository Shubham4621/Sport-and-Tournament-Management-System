from contextlib import contextmanager
from datetime import date, timedelta
import unittest
from unittest.mock import MagicMock, patch

from app import create_app
from app.db import transaction


class ManagementApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True})
        self.client = self.app.test_client()
        self.cursor = MagicMock()

    def transaction_context(self):
        @contextmanager
        def transaction():
            yield self.cursor

        return transaction

    @patch("app.management_api.transaction")
    def test_create_sport_uses_validated_values(self, transaction):
        self.cursor.lastrowid = 31
        transaction.side_effect = self.transaction_context()
        response = self.client.post(
            "/api/sports",
            json={"name": "  Badminton ", "description": "Indoor sport"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["sport"]["sport_id"], 31)
        self.cursor.execute.assert_called_once_with(
            "INSERT INTO Sports (name, description, is_active) VALUES (%s, %s, %s)",
            ("Badminton", "Indoor sport", True),
        )

    @patch("app.management_api.transaction")
    def test_invalid_sport_request_does_not_open_transaction(self, transaction):
        response = self.client.post("/api/sports", json={"name": " "})
        self.assertEqual(response.status_code, 400)
        transaction.assert_not_called()

    @patch("app.management_api.transaction")
    def test_create_tournament_preserves_publication_flag(self, transaction):
        self.cursor.fetchone.return_value = {"sport_id": 2}
        self.cursor.lastrowid = 44
        transaction.side_effect = self.transaction_context()
        response = self.client.post(
            "/api/tournaments",
            json={
                "sport_id": 2,
                "name": "College Cup",
                "competition_format": "team",
                "season": "2026",
                "start_date": "2026-11-01",
                "end_date": "2026-11-03",
                "is_published": True,
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.get_json()["tournament"]["is_published"])
        insert_call = self.cursor.execute.call_args_list[1]
        self.assertIn("INSERT INTO Tournaments", insert_call.args[0])
        self.assertTrue(insert_call.args[1][7])

    @patch("app.management_api.fetch_one", return_value={"tournament_id": 45})
    @patch("app.management_api.transaction")
    def test_partial_tournament_date_update_compares_date_types(
        self, transaction, fetch_one
    ):
        self.cursor.fetchone.side_effect = [
            {
                "tournament_id": 45,
                "start_date": date(2026, 11, 1),
                "end_date": date(2026, 11, 3),
            },
            {"has_history": 0},
        ]
        transaction.side_effect = self.transaction_context()
        response = self.client.put(
            "/api/tournaments/45",
            json={"start_date": "2026-11-02"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.cursor.execute.call_args_list[-1].args[1],
            ("2026-11-02", 45),
        )

    @patch("app.management_api.transaction")
    def test_team_registration_rejects_mismatched_sport(self, transaction):
        self.cursor.fetchone.side_effect = [
            {
                "tournament_id": 8,
                "sport_id": 3,
                "competition_format": "team",
                "status": "registration",
                "start_date": date.today() + timedelta(days=10),
            },
            {"team_id": 12, "sport_id": 4, "is_active": True},
        ]
        transaction.side_effect = self.transaction_context()
        response = self.client.post("/api/tournaments/8/teams", json={"team_id": 12})
        self.assertEqual(response.status_code, 400)
        self.assertIn("sport must match", response.get_json()["error"])
        self.assertEqual(self.cursor.execute.call_count, 2)

    @patch("app.management_api.transaction")
    def test_match_rejects_entries_from_another_tournament(self, transaction):
        self.cursor.fetchone.return_value = {
            "tournament_id": 8,
            "competition_format": "team",
            "status": "registration",
        }
        self.cursor.fetchall.return_value = []
        transaction.side_effect = self.transaction_context()
        response = self.client.post(
            "/api/matches",
            json={
                "tournament_id": 8,
                "match_number": 1,
                "entry_ids": [15, 16],
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("belong to this tournament", response.get_json()["error"])
        self.assertEqual(self.cursor.execute.call_count, 2)

    @patch("app.management_api.transaction")
    def test_result_declaration_writes_all_results_and_completes_atomically(self, transaction):
        self.cursor.fetchone.return_value = {
            "match_id": 10,
            "status": "live",
            "competition_format": "team",
        }
        self.cursor.fetchall.return_value = [
            {"entry_id": 20},
            {"entry_id": 21},
        ]
        transaction.side_effect = self.transaction_context()
        response = self.client.put(
            "/api/matches/10/results",
            json={
                "results": [
                    {"entry_id": 20, "outcome": "win"},
                    {"entry_id": 21, "outcome": "loss"},
                ]
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["results_saved"], 2)
        self.assertEqual(self.cursor.execute.call_count, 5)
        self.assertEqual(
            self.cursor.execute.call_args_list[-1].args[0],
            "UPDATE Matches SET status = 'completed' WHERE match_id = %s",
        )

    def test_registration_requires_team_id(self):
        response = self.client.post("/api/tournaments/8/teams", json={})
        self.assertEqual(response.status_code, 400)

    @patch("app.management_api.fetch_all")
    @patch("app.management_api.fetch_one", return_value={"match_id": 10, "match_status": "live"})
    def test_match_participants_read_includes_scores(self, fetch_one, fetch_all):
        fetch_all.side_effect = [
            [
                {
                    "entry_id": 21,
                    "team_id": 6,
                    "team_name": "Falcons",
                    "player_id": None,
                    "player_name": None,
                    "outcome": None,
                    "result_rank": None,
                    "official_note": None,
                }
            ],
            [
                {
                    "entry_id": 21,
                    "segment_number": 1,
                    "segment_label": "Set 1",
                    "numeric_value": 25,
                    "text_value": None,
                }
            ],
        ]
        response = self.client.get("/api/matches/10/participants?include_unpublished=true")
        self.assertEqual(response.status_code, 200)
        participant = response.get_json()["participants"][0]
        self.assertEqual(participant["entry_id"], 21)
        self.assertEqual(participant["scores"][0]["segment_label"], "Set 1")
        fetch_one.assert_called_once()

    @patch("app.management_api.transaction")
    def test_tournament_status_cannot_bypass_cancel_validation(self, transaction):
        response = self.client.put(
            "/api/tournaments/8",
            json={"status": "cancelled"},
        )
        self.assertEqual(response.status_code, 400)
        transaction.assert_not_called()

    @patch("app.db.get_connection")
    def test_transaction_commits_after_success(self, get_connection):
        connection = MagicMock()
        get_connection.return_value = connection
        with transaction():
            pass
        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()
        connection.close.assert_called_once()

    @patch("app.db.get_connection")
    def test_transaction_rolls_back_after_failure(self, get_connection):
        connection = MagicMock()
        get_connection.return_value = connection
        with self.assertRaisesRegex(RuntimeError, "test failure"):
            with transaction():
                raise RuntimeError("test failure")
        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()
        connection.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
