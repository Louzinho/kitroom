from datetime import date, datetime
from decimal import Decimal

import pymysql
from bson import ObjectId
from flask import Flask, jsonify, request, send_from_directory
from flask.json.provider import DefaultJSONProvider
from pymongo.errors import DuplicateKeyError, PyMongoError
from werkzeug.exceptions import HTTPException

from .config import Config
from .db import close_sql
from .errors import ApiError
from .routes import api


class ApiJson(DefaultJSONProvider):
    @staticmethod
    def default(o):
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        return DefaultJSONProvider.default(o)


SQL_MESSAGES = {
    1062: (409, "That value is already in use."),
    1451: (409, "This record is still used elsewhere, so it cannot be deleted."),
    1452: (422, "That linked record does not exist."),
    3819: (409, "That change would break a stock or price rule."),
    1213: (409, "Another order got in first. Try again."),
    1205: (409, "The shop is busy. Try again."),
}


def create_app(cfg=Config):
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.from_object(cfg)
    app.config["APP_CONFIG"] = cfg
    app.json = ApiJson(app)
    app.register_blueprint(api)
    app.teardown_appcontext(close_sql)

    @app.before_request
    def csrf_guard():
        # Browsers will not send this header cross-site without a CORS approval,
        # which this app never gives. SameSite=Lax cookies cover the rest.
        if request.path.startswith("/api/") and request.method not in ("GET", "HEAD", "OPTIONS"):
            if request.headers.get("X-Requested-With") != "KitRoom":
                raise ApiError("This request is missing its client header.", 403)

    @app.errorhandler(ApiError)
    def on_api_error(err):
        return jsonify({"error": err.message, **err.extra}), err.status

    @app.errorhandler(pymysql.err.MySQLError)
    def on_sql_error(err):
        code = err.args[0] if err.args else None
        status, message = SQL_MESSAGES.get(code, (503, "The database is not responding."))
        if status == 503:
            app.logger.exception(err)
        return jsonify({"error": message}), status

    @app.errorhandler(DuplicateKeyError)
    def on_duplicate_document(_err):
        return jsonify({"error": "You have already reviewed this shirt. Edit your review instead."}), 409

    @app.errorhandler(PyMongoError)
    def on_mongo_error(err):
        app.logger.exception(err)
        return jsonify({"error": "The document database is not responding."}), 503

    @app.errorhandler(HTTPException)
    def on_http_error(err):
        if request.path.startswith("/api/"):
            messages = {404: "No such endpoint.", 405: "Method not allowed.",
                        413: "That file is over the 5 MB limit."}
            return jsonify({"error": messages.get(err.code, err.description)}), err.code
        return err

    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    return app
