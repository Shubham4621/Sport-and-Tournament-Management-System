"""Provision a clean, separate Phase 8 test database.

The script is read-only unless --create is supplied. It never uses the
project database name as its target and never loads sample_data.sql.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
DATABASE_DIR = ROOT / "database"
BACKEND_DIR = ROOT / "backend"
PRODUCTION_DATABASE = "sports_tournament_management"
TEST_DATABASE = "sports_tournament_management_phase8_test"
DEPARTMENT_NAME = "Phase 8 Isolated Test Department"
SQL_FILES = ("schema.sql", "views.sql", "procedures.sql", "triggers.sql")
DATABASE_USE = re.compile(
    r"(?im)^\s*USE\s+`?sports_tournament_management`?\s*;"
)
DATABASE_CREATE = re.compile(
    r"(?is)CREATE\s+DATABASE\s+IF\s+NOT\s+EXISTS\s+"
    r"`?sports_tournament_management`?\s+"
    r"CHARACTER\s+SET\s+utf8mb4\s+COLLATE\s+utf8mb4_0900_ai_ci\s*;"
)
DELIMITER_DIRECTIVE = re.compile(r"^\s*DELIMITER\s+(\S+)\s*$", re.IGNORECASE)


def _without_sql_comments(value: str) -> str:
    value = re.sub(r"/\*.*?\*/", "", value, flags=re.DOTALL)
    value = re.sub(r"(?m)^\s*--[^\n]*", "", value)
    value = re.sub(r"(?m)^\s*#[^\n]*", "", value)
    return value


def split_mysql_script(script: str) -> list[str]:
    """Split the repository's SQL scripts, honoring DELIMITER and SQL quotes."""
    statements = []
    statement: list[str] = []
    delimiter = ";"
    quote = None
    block_comment = False
    line_comment = False
    index = 0

    while index < len(script):
        line_end = script.find("\n", index)
        if line_end == -1:
            line_end = len(script)
        line = script[index:line_end]

        if quote is None and not block_comment and not line_comment:
            directive = DELIMITER_DIRECTIVE.match(line)
            if directive and not _without_sql_comments("".join(statement)).strip():
                delimiter = directive.group(1)
                statement.clear()
                index = line_end + (line_end < len(script))
                continue

        while index < line_end:
            character = script[index]
            following = script[index + 1] if index + 1 < len(script) else ""

            if line_comment:
                statement.append(character)
                if character == "\n":
                    line_comment = False
                index += 1
                continue

            if block_comment:
                statement.append(character)
                if character == "*" and following == "/":
                    statement.append(following)
                    block_comment = False
                    index += 2
                else:
                    index += 1
                continue

            if quote is not None:
                statement.append(character)
                if character == "\\" and following:
                    statement.append(following)
                    index += 2
                    continue
                if character == quote:
                    if following == quote:
                        statement.append(following)
                        index += 2
                        continue
                    quote = None
                index += 1
                continue

            if character in ("'", '"', "`"):
                quote = character
                statement.append(character)
                index += 1
                continue
            if character == "/" and following == "*":
                block_comment = True
                statement.extend((character, following))
                index += 2
                continue
            if character == "#" or (
                character == "-"
                and following == "-"
                and (
                    index + 2 == len(script)
                    or script[index + 2].isspace()
                )
            ):
                line_comment = True
                statement.append(character)
                index += 1
                continue
            if script.startswith(delimiter, index):
                query = "".join(statement).strip()
                if _without_sql_comments(query).strip():
                    statements.append(query)
                statement.clear()
                index += len(delimiter)
                continue

            statement.append(character)
            index += 1

        if line_end < len(script):
            statement.append("\n")
            line_comment = False
            index = line_end + 1

    trailing = "".join(statement).strip()
    if _without_sql_comments(trailing).strip():
        raise ValueError("SQL script ends with an unterminated statement.")
    return statements


def load_sql_file(name: str) -> list[str]:
    source = (DATABASE_DIR / name).read_text(encoding="utf-8")
    if name == "schema.sql":
        source, create_count = DATABASE_CREATE.subn("", source)
        if create_count != 1:
            raise ValueError("schema.sql database creation directive changed.")
    source, use_count = DATABASE_USE.subn(
        f"USE `{TEST_DATABASE}`;", source
    )
    if use_count != 1:
        raise ValueError(f"{name} must contain exactly one database USE directive.")
    return split_mysql_script(source)


def database_config() -> dict[str, object]:
    load_dotenv(BACKEND_DIR / ".env")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    if not user or not password:
        raise ValueError(
            "DB_USER and DB_PASSWORD must be configured in backend/.env "
            "or the process environment."
        )
    try:
        port = int(os.getenv("DB_PORT", "3306"))
    except ValueError as error:
        raise ValueError("DB_PORT must be an integer.") from error
    if not 1 <= port <= 65535:
        raise ValueError("DB_PORT must be between 1 and 65535.")
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": port,
        "user": user,
        "password": password,
        "connection_timeout": 5,
        "autocommit": True,
    }


def verify_clean_database(connection) -> tuple[int, str]:
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = %s AND table_type = 'BASE TABLE'
            """,
            (TEST_DATABASE,),
        )
        table_count = cursor.fetchone()[0]
        cursor.execute(f"USE `{TEST_DATABASE}`")
        for table in (
            "Admins",
            "Sports",
            "Departments",
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
        ):
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            expected_rows = 1 if table == "Departments" else 0
            if cursor.fetchone()[0] != expected_rows:
                raise RuntimeError(
                    f"Unexpected row count after setup: {table}."
                )

        cursor.execute(
            """
            SELECT COUNT(*) FROM Departments
            WHERE department_name = %s
            """,
            (DEPARTMENT_NAME,),
        )
        if cursor.fetchone()[0] != 1:
            raise RuntimeError("The isolated department fixture is missing.")
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.views
            WHERE table_schema = %s
            """,
            (TEST_DATABASE,),
        )
        if cursor.fetchone()[0] != 5:
            raise RuntimeError("Expected five Phase 3 views in the test database.")
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.routines
            WHERE routine_schema = %s AND routine_type = 'PROCEDURE'
            """,
            (TEST_DATABASE,),
        )
        if cursor.fetchone()[0] != 2:
            raise RuntimeError("Expected two Phase 3 procedures in the test database.")
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.triggers
            WHERE trigger_schema = %s
            """,
            (TEST_DATABASE,),
        )
        if cursor.fetchone()[0] != 6:
            raise RuntimeError("Expected six Phase 3 triggers in the test database.")
        cursor.execute(
            "SELECT DATABASE(), VERSION(), "
            "(SELECT department_id FROM Departments WHERE department_name = %s)",
            (DEPARTMENT_NAME,),
        )
        _, version, department_id = cursor.fetchone()
        if table_count != 15:
            raise RuntimeError(f"Expected 15 tables, found {table_count}.")
        return int(department_id), str(version)
    finally:
        cursor.close()


def create_database() -> None:
    config = database_config()
    connection = mysql.connector.connect(**config)
    cursor = connection.cursor()
    created = False
    try:
        cursor.execute(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name = %s",
            (TEST_DATABASE,),
        )
        if cursor.fetchone() is not None:
            raise RuntimeError(
                f"{TEST_DATABASE} already exists. Refusing to modify or replace it."
            )
        cursor.execute(
            f"CREATE DATABASE `{TEST_DATABASE}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
        )
        created = True
        cursor.execute(f"USE `{TEST_DATABASE}`")

        for sql_file in SQL_FILES:
            for statement in load_sql_file(sql_file):
                try:
                    cursor.execute(statement)
                except mysql.connector.Error as error:
                    raise RuntimeError(
                        f"Failed while applying {sql_file}; "
                        "the isolated database may be partially initialized."
                    ) from error

        cursor.execute(
            "INSERT INTO Departments (department_name, description) "
            "VALUES (%s, %s)",
            (
                DEPARTMENT_NAME,
                "Setup fixture for isolated Phase 8 tests.",
            ),
        )
        department_id, version = verify_clean_database(connection)
        print(
            f"Created isolated database {TEST_DATABASE}; "
            f"MySQL {version}; 15 tables, 5 views, 2 procedures, "
            f"6 triggers; test department ID {department_id}."
        )
    except Exception:
        if created:
            print(
                f"Setup did not complete. {TEST_DATABASE} was left in place "
                "for inspection; it was not dropped.",
                file=sys.stderr,
            )
        raise
    finally:
        cursor.close()
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Plan or provision a clean Phase 8 test database."
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="Create and provision the isolated test database.",
    )
    args = parser.parse_args()

    try:
        statements = {
            name: load_sql_file(name)
            for name in SQL_FILES
        }
        print(f"Target database: {TEST_DATABASE}")
        print(f"Existing project database: {PRODUCTION_DATABASE} (not selected)")
        print("Sample-data script: not loaded")
        print(
            "Setup fixture: one department "
            f"({DEPARTMENT_NAME!r})"
        )
        print(
            "Source SQL statements: "
            + ", ".join(f"{name}={len(sql)}" for name, sql in statements.items())
        )
        if not args.create:
            print("Plan only; no database connection or writes were made.")
            print("Pass --create when ready to create the isolated database.")
            return 0
        create_database()
    except (OSError, ValueError, RuntimeError, mysql.connector.Error) as error:
        print(f"Phase 8 database setup failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
