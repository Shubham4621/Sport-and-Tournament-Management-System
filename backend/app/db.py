from contextlib import contextmanager
import os

import mysql.connector


class DatabaseConfigurationError(RuntimeError):
    pass


def get_connection():
    required = ("DB_USER", "DB_PASSWORD")
    missing = [name for name in required if os.getenv(name) is None]
    if missing:
        raise DatabaseConfigurationError(
            "Missing required database environment variable(s): "
            + ", ".join(missing)
        )

    try:
        port = int(os.getenv("DB_PORT", "3306"))
    except ValueError as error:
        raise DatabaseConfigurationError("DB_PORT must be an integer.") from error
    if not 1 <= port <= 65535:
        raise DatabaseConfigurationError("DB_PORT must be between 1 and 65535.")

    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=port,
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.getenv("DB_NAME", "sports_tournament_management"),
        charset="utf8mb4",
        use_unicode=True,
        connection_timeout=5,
    )


def fetch_all(sql, params=()):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def fetch_one(sql, params=()):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        return cursor.fetchone()
    finally:
        cursor.close()
        connection.close()


def execute(sql, params=()):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(sql, params)
        connection.commit()
        return cursor.lastrowid
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


@contextmanager
def transaction():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def fetch_procedure_rows(sql, params=()):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        while cursor.nextset():
            if cursor.with_rows:
                cursor.fetchall()
        return rows
    finally:
        cursor.close()
        connection.close()


def fetch_procedure_result_sets(sql, params=()):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        result_sets = []
        while True:
            if cursor.with_rows:
                result_sets.append(cursor.fetchall())
            if not cursor.nextset():
                break
        return result_sets
    finally:
        cursor.close()
        connection.close()
