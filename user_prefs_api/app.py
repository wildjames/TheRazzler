import logging
from datetime import datetime, timedelta
from functools import wraps

import jwt
import yaml
from flask import Flask, jsonify, request
from flask_cors import CORS

from signal_interface.dataclasses import OutgoingMessage
from utils.configuration import Config
from utils.local_storage import load_file, load_phonebook
from utils.mongo import (
    UserPreferencesUpdate,
    clear_user_preferences,
    get_mongo_db,
    get_user_preferences,
    initialize_preferences_collection,
    update_user_preferences,
)

from .utils import fetch_cached_otp, get_otp, publish_message

# Load the configuration from the data directory
config = Config(**yaml.safe_load(load_file("config.yaml")))

redis_config = config.redis

rabbit_config = config.rabbitmq

db = get_mongo_db(config.mongodb)
preferences_collection = initialize_preferences_collection(db)

app = Flask(__name__)
CORS(
    app,
    origins=[
        "localhost",
        "127.0.0.1",
        "https://razzler-web.wildjames.com",
    ],
)
app.logger.setLevel(logging.INFO)


@app.route("/", methods=["GET"])
def health_check():
    return "OK", 200


def validate_jwt(token):
    try:
        # Decode the token using the same secret key used for encoding
        payload = jwt.decode(
            token, config.general.jwt_secret, algorithms=["HS256"]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401


def jwt_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract token from the Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Authorization header is missing"}), 401

        parts = auth_header.split()
        if parts[0].lower() != "bearer":
            return (
                jsonify(
                    {"error": "Authorization header must start with Bearer"}
                ),
                401,
            )
        elif len(parts) == 1:
            return jsonify({"error": "Token not found"}), 401
        elif len(parts) > 2:
            return (
                jsonify(
                    {"error": "Authorization header must be Bearer token"}
                ),
                401,
            )

        token = parts[1]
        result = validate_jwt(token)
        if isinstance(result, tuple):  # Error tuple returned
            return result

        # Set the user_id in the flask global g, which is accessible to the route
        request.user_id = result["user_id"]
        return f(*args, **kwargs)

    return decorated_function


@app.route("/preferences", methods=["GET"])
@jwt_required
def get_preferences():
    user_id = request.user_id
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    try:
        preferences = get_user_preferences(preferences_collection, user_id)
        return jsonify(preferences.model_dump()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/preferences", methods=["PUT"])
@jwt_required
def update_preferences():
    user_id = request.user_id
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    try:
        update_data = UserPreferencesUpdate(**request.json)
        update_user_preferences(preferences_collection, user_id, update_data)
        return jsonify({"message": "Preferences updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/preferences", methods=["DELETE"])
@jwt_required
def delete_preferences():
    user_id = request.user_id
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    try:
        clear_user_preferences(preferences_collection, user_id)
        return jsonify({"message": "Preferences cleared"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/login/issue_otp", methods=["GET"])
async def issue_otp():
    user_id = request.args.get("user_number")
    if not user_id:
        return jsonify({"error": "user_number is required"}), 400

    if user_id.startswith("0"):
        user_id = "+44" + user_id[1:]

    phonebook = load_phonebook()
    app.logger.info(phonebook.contacts)
    app.logger.info(f"Do we have {user_id}?")
    contact = phonebook.get_contact(user_id)
    app.logger.info(contact)

    # Issue an OTP here
    try:
        otp = get_otp(user_id, redis_config)
    except:
        return jsonify({"error": "User not recognised"}), 404

    # And the OTP needs to be added to the rabbit queue, to be sent to the user
    msg = OutgoingMessage(
        recipient=user_id,
        message=f"Your OTP is: {otp}",
    )
    try:
        # This will be picked up by a producer, and sent to the user
        await publish_message(msg, rabbit_config)
    except:
        return jsonify({"error": "Failed to send OTP"}), 500

    return jsonify({"message": "OTP issued"}), 200


@app.route("/login/verify_otp", methods=["GET"])
def verify_otp():
    user_id = request.args.get("user_number")
    otp = request.args.get("otp")

    if not user_id or not otp:
        return jsonify({"error": "user_number and otp are required"}), 400

    if user_id.startswith("0"):
        user_id = "+44" + user_id[1:]

    app.logger.info(f"Verifying OTP for {user_id}: user submitted {otp}")

    # Verify the OTP
    stored_otp = fetch_cached_otp(user_id, redis_config)
    app.logger.info(f"Stored OTP: {stored_otp}")

    if stored_otp == otp:
        # Get the corresponding UUID, and use that rather than a phone number
        user_id = load_phonebook().get_contact(user_id).uuid

        exp = datetime.now() + timedelta(days=config.general.jwt_expiry_days)
        payload = {
            "user_id": user_id,
            "exp": exp,
        }

        token = jwt.encode(payload, key=config.general.jwt_secret)

        return jsonify({"token": token}), 200

    else:
        return jsonify({"error": "Invalid OTP"}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
