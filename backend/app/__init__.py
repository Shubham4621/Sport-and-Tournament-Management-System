import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from mysql.connector import Error as MySQLError
from werkzeug.exceptions import HTTPException

from .api import api
from .db import DatabaseConfigurationError


def create_app(test_config=None):
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

    app = Flask(__name__)
    app.config.from_mapping(
        DEBUG=os.getenv("FLASK_DEBUG", "false").strip().lower() == "true",
        JSON_SORT_KEYS=False,
    )
    if test_config:
        app.config.update(test_config)

    origins = [
        origin.strip()
        for origin in os.getenv(
            "FRONTEND_ORIGINS", "http://localhost:5173"
        ).split(",")
        if origin.strip()
    ]
    CORS(
        app,
        resources={r"/api/*": {"origins": origins}},
        allow_headers=["Content-Type"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    app.register_blueprint(api, url_prefix="/api")
    from .management_api import management_api

    app.register_blueprint(management_api, url_prefix="/api")

    @app.errorhandler(MySQLError)
    def handle_database_error(error):
        app.logger.exception("Database request failed")
        if getattr(error, "errno", None) == 1062:
            return jsonify(error="A record with the same unique value already exists."), 409
        if getattr(error, "errno", None) == 1451:
            return jsonify(
                error="This record is referenced by other records and cannot be deleted."
            ), 409
        if getattr(error, "errno", None) in (1452, 3819, 4025, 1644):
            return jsonify(error="The request conflicts with database constraints."), 400
        return jsonify(error="Database operation failed."), 503

    @app.errorhandler(DatabaseConfigurationError)
    def handle_database_configuration_error(error):
        app.logger.error("Database configuration is incomplete or invalid.")
        return jsonify(error="Database configuration is unavailable."), 503

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify(error=error.description), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception("Unexpected API error")
        return jsonify(error="Internal server error."), 500

    return app
