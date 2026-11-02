import os
import unittest
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import mysql.connector

from app import create_app


TEST_DATABASE = "sports_tournament_management_phase8_test"
PRODUCTION_DATABASE = "sports_tournament_management"
TEST_DEPARTMENT = "Phase 8 Isolated Test Department"
REAL_CONNECT = mysql.connector.connect


class Phase8MySQLWorkflowTests(unittest.TestCase):
    """Opt-in end-to-end test; creates records and intentionally retains them."""

    @classmethod
    def setUpClass(cls):
        if os.getenv("RUN_PHASE8_INTEGRATION") != "1":
            raise unittest.SkipTest(
                "Set RUN_PHASE8_INTEGRATION=1 to run real MySQL workflow tests."
            )
        configured_database = os.getenv("DB_NAME")
        if configured_database != TEST_DATABASE:
            raise RuntimeError(
                "Refusing Phase 8 writes: DB_NAME must be exactly "
                f"{TEST_DATABASE!r}, not {configured_database!r}."
            )

        cls.connection_patch = patch(
            "mysql.connector.connect",
            side_effect=cls._connect_only_to_test_database,
        )
        cls.connection_patch.start()
        cls.app = create_app({"TESTING": True})
        cls.client = cls.app.test_client()
        cls.run_id = uuid.uuid4().hex[:12]

        # This connection is subject to the same guard as every API connection.
        with cls._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT department_id FROM Departments WHERE department_name = %s",
                (TEST_DEPARTMENT,),
            )
            row = cursor.fetchone()
            cursor.close()
        if row is None:
            cls.connection_patch.stop()
            raise RuntimeError(
                "Isolated Phase 8 test department fixture is missing."
            )
        cls.department_id = int(row[0])

    @classmethod
    def tearDownClass(cls):
        patcher = getattr(cls, "connection_patch", None)
        if patcher is not None:
            patcher.stop()

    @staticmethod
    def _connect_only_to_test_database(*args, **kwargs):
        requested_database = kwargs.get("database")
        if requested_database == PRODUCTION_DATABASE:
            raise RuntimeError(
                "ABORT: attempted to connect to the original project database."
            )
        if requested_database != TEST_DATABASE:
            raise RuntimeError(
                "ABORT: every integration connection must explicitly select "
                f"{TEST_DATABASE!r}."
            )

        connection = REAL_CONNECT(*args, **kwargs)
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE()")
            selected_database = cursor.fetchone()[0]
            cursor.close()
            if selected_database == PRODUCTION_DATABASE:
                raise RuntimeError(
                    "ABORT: SELECT DATABASE() returned the original database."
                )
            if selected_database != TEST_DATABASE:
                raise RuntimeError(
                    "ABORT: SELECT DATABASE() did not return the isolated "
                    f"database {TEST_DATABASE!r}."
                )
            return connection
        except Exception:
            connection.close()
            raise

    @classmethod
    def _connection(cls):
        return mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=TEST_DATABASE,
            charset="utf8mb4",
            use_unicode=True,
            connection_timeout=5,
        )

    def _verify_selected_database(self):
        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE()")
            selected_database = cursor.fetchone()[0]
            cursor.close()
        self.assertEqual(selected_database, TEST_DATABASE)
        self.assertNotEqual(selected_database, PRODUCTION_DATABASE)

    def _write(self, method, path, *, json=None):
        # Explicit pre-write assertion plus the connection-level guard above.
        self._verify_selected_database()
        response = self.client.open(path, method=method, json=json)
        return response

    def _read(self, sql, params=()):
        with self._connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            cursor.close()
        return rows

    def _count(self, table, where="", params=()):
        allowed_tables = {
            "Students",
            "Players",
            "Player_Sports",
            "Teams",
            "Team_Memberships",
            "Tournaments",
            "Tournament_Scoring_Rules",
            "Tournament_Entries",
            "Matches",
            "Match_Entries",
            "Match_Scores",
            "Match_Results",
        }
        self.assertIn(table, allowed_tables)
        rows = self._read(
            f"SELECT COUNT(*) AS row_count FROM `{table}` {where}",
            params,
        )
        return int(rows[0]["row_count"])

    def _expect(self, response, status):
        self.assertEqual(
            response.status_code,
            status,
            response.get_json(silent=True),
        )
        return response.get_json()

    def test_complete_real_mysql_workflow_and_rejections(self):
        self._verify_selected_database()
        before_stats = self._expect(
            self.client.get("/api/dashboard/stats"),
            200,
        )["stats"]

        suffix = self.run_id
        sport_name = f"E2E-{suffix}-Sport"
        other_sport_name = f"E2E-{suffix}-OtherSport"
        student_numbers = [f"E2E-{suffix}-{number}" for number in (1, 2, 3)]

        # 1. Create a sport and another sport used to test mismatched teams.
        sport = self._expect(
            self._write(
                "POST",
                "/api/sports",
                json={
                    "name": sport_name,
                    "description": f"Phase 8 integration {suffix}",
                    "is_active": True,
                },
            ),
            201,
        )["sport"]
        sport_id = sport["sport_id"]
        other_sport = self._expect(
            self._write(
                "POST",
                "/api/sports",
                json={"name": other_sport_name, "is_active": True},
            ),
            201,
        )["sport"]
        other_sport_id = other_sport["sport_id"]

        # 2-3. Create two workflow students/players and one ineligible probe.
        students = []
        players = []
        for index, student_number in enumerate(student_numbers, start=1):
            student = self._expect(
                self._write(
                    "POST",
                    "/api/students",
                    json={
                        "student_number": student_number,
                        "first_name": f"E2E{index}",
                        "last_name": suffix,
                        "email": None,
                        "department_id": self.department_id,
                        "enrollment_status": "active",
                    },
                ),
                201,
            )["student"]
            students.append(student)
            player = self._expect(
                self._write(
                    "POST",
                    f"/api/students/{student['student_id']}/player",
                    json={"is_active": True},
                ),
                201,
            )["player"]
            players.append(player)

        # 4. Only the two match players are eligible in the selected sport.
        for player in players[:2]:
            self._expect(
                self._write(
                    "POST",
                    f"/api/players/{player['player_id']}/eligibility",
                    json={
                        "sport_id": sport_id,
                        "eligible_from": date.today().isoformat(),
                        "eligible_to": None,
                    },
                ),
                201,
            )

        # 5. Create two matching teams and a third team of a different sport.
        teams = []
        for index in (1, 2):
            team = self._expect(
                self._write(
                    "POST",
                    "/api/teams",
                    json={
                        "sport_id": sport_id,
                        "department_id": self.department_id,
                        "name": f"E2E-{suffix}-Team-{index}",
                        "team_code": f"E2E-{suffix}-{index}",
                        "is_active": True,
                    },
                ),
                201,
            )["team"]
            teams.append(team)
        invalid_team = self._expect(
            self._write(
                "POST",
                "/api/teams",
                json={
                    "sport_id": other_sport_id,
                    "department_id": self.department_id,
                    "name": f"E2E-{suffix}-WrongSportTeam",
                    "team_code": f"E2E-{suffix}-X",
                    "is_active": True,
                },
            ),
            201,
        )["team"]

        # 6. Eligible players can join their respective teams.
        for team, player in zip(teams, players[:2]):
            self._expect(
                self._write(
                    "POST",
                    f"/api/teams/{team['team_id']}/members",
                    json={
                        "player_id": player["player_id"],
                        "membership_from": date.today().isoformat(),
                        "membership_to": None,
                    },
                ),
                201,
            )

        # Business-rule test: DB trigger must reject the ineligible player.
        memberships_before = self._count("Team_Memberships")
        ineligible_response = self._write(
            "POST",
            f"/api/teams/{teams[0]['team_id']}/members",
            json={
                "player_id": players[2]["player_id"],
                "membership_from": date.today().isoformat(),
                "membership_to": None,
            },
        )
        self.assertIn(ineligible_response.status_code, (400, 409))
        self.assertEqual(
            self._count("Team_Memberships"),
            memberships_before,
            "Rejected membership must not leave a partial row.",
        )

        # Foreign-key test directly against InnoDB in an isolated transaction.
        invalid_fk_code = None
        self._verify_selected_database()
        with self._connection() as connection:
            cursor = connection.cursor()
            connection.start_transaction()
            try:
                cursor.execute(
                    """
                    INSERT INTO Teams (
                        sport_id, department_id, name, team_code, is_active
                    )
                    VALUES (%s, %s, %s, %s, TRUE)
                    """,
                    (
                        4_294_967_295,
                        self.department_id,
                        f"E2E-{suffix}-InvalidFK",
                        f"E2E-{suffix}-FK",
                    ),
                )
                self.fail("MySQL accepted a team with a nonexistent sport FK.")
            except mysql.connector.Error as error:
                invalid_fk_code = error.errno
                connection.rollback()
            finally:
                cursor.close()
        self.assertEqual(invalid_fk_code, 1452)
        self.assertEqual(
            self._count(
                "Teams",
                "WHERE name = %s",
                (f"E2E-{suffix}-InvalidFK",),
            ),
            0,
        )

        # 7. Create tournament with scoring rules and register both teams.
        starts = date.today() + timedelta(days=10)
        ends = starts + timedelta(days=2)
        tournament = self._expect(
            self._write(
                "POST",
                "/api/tournaments",
                json={
                    "sport_id": sport_id,
                    "name": f"E2E-{suffix}-Cup",
                    "competition_format": "team",
                    "season": suffix,
                    "start_date": starts.isoformat(),
                    "end_date": ends.isoformat(),
                    "status": "registration",
                    "is_published": True,
                    "description": "Isolated MySQL workflow test",
                    "scoring_rules": {
                        "points_for_win": 3,
                        "points_for_draw": 1,
                        "points_for_loss": 0,
                    },
                },
            ),
            201,
        )["tournament"]
        tournament_id = tournament["tournament_id"]
        entries = []
        for team in teams:
            entries.append(
                self._expect(
                    self._write(
                        "POST",
                        f"/api/tournaments/{tournament_id}/teams",
                        json={"team_id": team["team_id"]},
                    ),
                    201,
                )["entry"]
            )

        entries_before_duplicate = self._count(
            "Tournament_Entries",
            "WHERE tournament_id = %s",
            (tournament_id,),
        )
        duplicate_registration = self._write(
            "POST",
            f"/api/tournaments/{tournament_id}/teams",
            json={"team_id": teams[0]["team_id"]},
        )
        self.assertEqual(duplicate_registration.status_code, 409)
        self.assertEqual(
            self._count(
                "Tournament_Entries",
                "WHERE tournament_id = %s",
                (tournament_id,),
            ),
            entries_before_duplicate,
        )

        wrong_team_registration = self._write(
            "POST",
            f"/api/tournaments/{tournament_id}/teams",
            json={"team_id": invalid_team["team_id"]},
        )
        self.assertEqual(wrong_team_registration.status_code, 400)
        self.assertEqual(
            self._count(
                "Tournament_Entries",
                "WHERE tournament_id = %s AND team_id = %s",
                (tournament_id, invalid_team["team_id"]),
            ),
            0,
        )

        # Also prove trigger-enforced format/sport rules at the SQL boundary.
        self._verify_selected_database()
        trigger_code = None
        with self._connection() as connection:
            cursor = connection.cursor()
            connection.start_transaction()
            try:
                cursor.execute(
                    """
                    INSERT INTO Tournament_Entries (
                        tournament_id, team_id, status
                    )
                    VALUES (%s, %s, 'registered')
                    """,
                    (tournament_id, invalid_team["team_id"]),
                )
                self.fail("Tournament-entry trigger accepted a wrong-sport team.")
            except mysql.connector.Error as error:
                trigger_code = error.errno
                connection.rollback()
            finally:
                cursor.close()
        self.assertEqual(trigger_code, 1644)
        self.assertEqual(
            self._count(
                "Tournament_Entries",
                "WHERE tournament_id = %s AND team_id = %s",
                (tournament_id, invalid_team["team_id"]),
            ),
            0,
        )

        # 8. Register the second team in another tournament to test cross-
        # tournament match participants against the real database.
        other_tournament = self._expect(
            self._write(
                "POST",
                "/api/tournaments",
                json={
                    "sport_id": sport_id,
                    "name": f"E2E-{suffix}-OtherCup",
                    "competition_format": "team",
                    "season": f"{suffix}-other",
                    "start_date": starts.isoformat(),
                    "end_date": ends.isoformat(),
                    "status": "registration",
                    "is_published": True,
                },
            ),
            201,
        )["tournament"]
        foreign_entry = self._expect(
            self._write(
                "POST",
                f"/api/tournaments/{other_tournament['tournament_id']}/teams",
                json={"team_id": teams[1]["team_id"]},
            ),
            201,
        )["entry"]

        # 9. Invalid participant references must not create match/entry rows.
        matches_before_invalid = self._count(
            "Matches",
            "WHERE tournament_id = %s",
            (tournament_id,),
        )
        cross_tournament_match = self._write(
            "POST",
            "/api/matches",
            json={
                "tournament_id": tournament_id,
                "match_number": 99,
                "entry_ids": [entries[0]["entry_id"], foreign_entry["entry_id"]],
                "scheduled_at": datetime.combine(
                    starts, datetime.min.time()
                ).isoformat(),
            },
        )
        self.assertEqual(cross_tournament_match.status_code, 400)
        self.assertEqual(
            self._count(
                "Matches",
                "WHERE tournament_id = %s",
                (tournament_id,),
            ),
            matches_before_invalid,
            "Rejected match must not leave a match row.",
        )

        # 10. Schedule a valid match between both registered teams.
        scheduled_at = datetime.combine(
            starts, datetime.min.time()
        ) + timedelta(hours=12)
        match = self._expect(
            self._write(
                "POST",
                "/api/matches",
                json={
                    "tournament_id": tournament_id,
                    "match_number": 1,
                    "entry_ids": [entry["entry_id"] for entry in entries],
                    "scheduled_at": scheduled_at.isoformat(),
                    "stage": "Final",
                    "round_name": "Final",
                    "venue": "Isolated Test Venue",
                },
            ),
            201,
        )["match"]
        match_id = match["match_id"]
        self.assertEqual(
            self._count("Match_Entries", "WHERE match_id = %s", (match_id,)),
            2,
        )

        # Duplicate match number fails at MySQL and leaves no partial rows.
        duplicate_match = self._write(
            "POST",
            "/api/matches",
            json={
                "tournament_id": tournament_id,
                "match_number": 1,
                "entry_ids": [entry["entry_id"] for entry in entries],
                "scheduled_at": (scheduled_at + timedelta(hours=1)).isoformat(),
            },
        )
        self.assertEqual(duplicate_match.status_code, 409)
        self.assertEqual(
            self._count("Matches", "WHERE tournament_id = %s", (tournament_id,)),
            1,
        )
        self.assertEqual(
            self._count("Match_Entries", "WHERE match_id = %s", (match_id,)),
            2,
        )

        # 11. Enter one numeric score segment for each match participant.
        score_payload = [
            {
                "entry_id": entries[0]["entry_id"],
                "segment_number": 1,
                "segment_label": "E2E segment",
                "numeric_value": 2,
                "text_value": None,
            },
            {
                "entry_id": entries[1]["entry_id"],
                "segment_number": 1,
                "segment_label": "E2E segment",
                "numeric_value": 1,
                "text_value": None,
            },
        ]
        score_result = self._expect(
            self._write(
                "PUT",
                f"/api/matches/{match_id}/scores",
                json={"scores": score_payload},
            ),
            200,
        )
        self.assertEqual(score_result["scores_saved"], 2)
        self.assertEqual(
            self._count("Match_Scores", "WHERE match_id = %s", (match_id,)),
            2,
        )

        # 12. Invalid result must not write any result or complete the match.
        invalid_result = self._write(
            "PUT",
            f"/api/matches/{match_id}/results",
            json={
                "results": [
                    {"entry_id": entries[0]["entry_id"], "outcome": "win"},
                    {"entry_id": entries[1]["entry_id"], "outcome": "win"},
                ]
            },
        )
        self.assertEqual(invalid_result.status_code, 400)
        self.assertEqual(
            self._count("Match_Results", "WHERE match_id = %s", (match_id,)),
            0,
        )
        self.assertEqual(
            self._read(
                "SELECT status FROM Matches WHERE match_id = %s",
                (match_id,),
            )[0]["status"],
            "scheduled",
        )

        # 13. Declare a valid result; result rows and match completion are atomic.
        completed = self._expect(
            self._write(
                "PUT",
                f"/api/matches/{match_id}/results",
                json={
                    "results": [
                        {
                            "entry_id": entries[0]["entry_id"],
                            "outcome": "win",
                            "result_rank": None,
                            "official_note": f"E2E winner {suffix}",
                        },
                        {
                            "entry_id": entries[1]["entry_id"],
                            "outcome": "loss",
                            "result_rank": None,
                            "official_note": f"E2E result {suffix}",
                        },
                    ]
                },
            ),
            200,
        )
        self.assertEqual(completed["match_status"], "completed")
        self.assertEqual(completed["results_saved"], 2)
        self.assertEqual(
            self._read(
                "SELECT status FROM Matches WHERE match_id = %s",
                (match_id,),
            )[0]["status"],
            "completed",
        )
        self.assertEqual(
            self._count("Match_Results", "WHERE match_id = %s", (match_id,)),
            2,
        )

        # 14. Verify standings, persisted scores/results, report procedure.
        standings = self._expect(
            self.client.get(f"/api/tournaments/{tournament_id}/standings"),
            200,
        )["standings"]
        self.assertEqual(len(standings), 2)
        by_entry = {row["entry_id"]: row for row in standings}
        winner = by_entry[entries[0]["entry_id"]]
        runner_up = by_entry[entries[1]["entry_id"]]
        self.assertEqual(int(winner["wins"]), 1)
        self.assertEqual(int(winner["losses"]), 0)
        self.assertEqual(int(winner["draws"]), 0)
        self.assertEqual(int(winner["played_matches"]), 1)
        self.assertEqual(Decimal(str(winner["total_points"])), Decimal("3.00"))
        self.assertEqual(int(runner_up["wins"]), 0)
        self.assertEqual(int(runner_up["losses"]), 1)
        self.assertEqual(int(runner_up["played_matches"]), 1)
        self.assertEqual(Decimal(str(runner_up["total_points"])), Decimal("0.00"))

        tournament_report = self._expect(
            self.client.get(
                f"/api/reports/tournaments/{tournament_id}"
                "?include_unpublished=true"
            ),
            200,
        )
        report = tournament_report["tournament"]
        self.assertEqual(report["registered_entries"], 2)
        self.assertEqual(report["total_matches"], 1)
        self.assertEqual(report["completed_matches"], 1)
        self.assertEqual(report["declared_results"], 2)
        self.assertEqual(
            sum(row["participant_results"] for row in tournament_report["result_summary"]),
            2,
        )

        match_report = self._expect(
            self.client.get(
                "/api/reports/match-results"
                f"?tournament_id={tournament_id}&include_unpublished=true"
            ),
            200,
        )["items"]
        self.assertEqual(len(match_report), 2)
        scores_and_results = self._expect(
            self.client.get(
                f"/api/matches/{match_id}/results?include_unpublished=true"
            ),
            200,
        )["results"]
        self.assertEqual(len(scores_and_results), 2)
        self.assertTrue(all(row["score_summary"] for row in scores_and_results))

        # Tournament winner reporting requires tournament status completed.
        self._expect(
            self._write(
                "PATCH",
                f"/api/tournaments/{tournament_id}/status",
                json={"status": "completed"},
            ),
            200,
        )
        winner_rows = self._expect(
            self.client.get("/api/reports/tournament-winners"),
            200,
        )["items"]
        self.assertTrue(
            any(
                row["tournament_id"] == tournament_id
                and row["entry_id"] == entries[0]["entry_id"]
                for row in winner_rows
            )
        )

        # 15. Dashboard/report deltas are isolated to the records from this run.
        after_stats = self._expect(
            self.client.get("/api/dashboard/stats"),
            200,
        )["stats"]
        expected_deltas = {
            "students": 3,
            "total_players": 3,
            "active_players": 3,
            "total_teams": 3,
            "active_teams": 3,
            "total_tournaments": 2,
            "published_tournaments": 2,
            "total_matches": 1,
            "completed_matches": 1,
            "tournament_participants": 3,
            "total_match_results": 2,
        }
        for key, delta in expected_deltas.items():
            self.assertEqual(
                int(after_stats[key]) - int(before_stats[key]),
                delta,
                f"Unexpected dashboard delta for {key}.",
            )

        summary = self._expect(self.client.get("/api/reports/summary"), 200)[
            "summary"
        ]
        self.assertEqual(int(summary["total_players"]), int(after_stats["total_players"]))
        self.assertEqual(int(summary["total_teams"]), int(after_stats["total_teams"]))
        self.assertGreaterEqual(
            int(summary["completed_match_wins"]),
            1,
        )

        # Final DB verification and safety assertion.
        self._verify_selected_database()
        self.assertEqual(
            self._count("Player_Sports", "WHERE sport_id = %s", (sport_id,)),
            2,
        )
        self.assertEqual(
            self._count(
                "Team_Memberships",
                "WHERE team_id IN (%s, %s)",
                (teams[0]["team_id"], teams[1]["team_id"]),
            ),
            2,
        )


if __name__ == "__main__":
    unittest.main()
