import yaml
from flask import Flask, jsonify, request

from utils.configuration import Config
from utils.local_storage import load_file
from utils.mongo import (
    MongoConfig,
    UserPreferencesUpdate,
    clear_user_preferences,
    get_mongo_db,
    get_user_preferences,
    initialize_preferences_collection,
    update_user_preferences,
)

# Load the configuration from the data directory
config = yaml.safe_load(load_file("config.yaml"))
config = Config(**config).mongodb

db = get_mongo_db(config)
preferences_collection = initialize_preferences_collection(db)

app = Flask(__name__)


@app.route("/preferences", methods=["GET"])
def get_preferences():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    try:
        preferences = get_user_preferences(preferences_collection, user_id)
        return jsonify(preferences.model_dump()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/preferences", methods=["PUT"])
def update_preferences():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    try:
        update_data = UserPreferencesUpdate(**request.json)
        update_user_preferences(preferences_collection, user_id, update_data)
        return jsonify({"message": "Preferences updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/preferences", methods=["DELETE"])
def delete_preferences():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    try:
        clear_user_preferences(preferences_collection, user_id)
        return jsonify({"message": "Preferences cleared"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
