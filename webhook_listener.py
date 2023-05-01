from flask import Flask, request
import hmac
import os
import subprocess

app = Flask(__name__)

# Set your webhook secret and service name here
with open("webhook_secret.txt", "r") as f:
    WEBHOOK_SECRET = f.readline().strip()
SERVICE_NAME = "therazzler.service"

@app.route("/", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Hub-Signature-256")
    payload = request.data

    # Verify the request
    if not verify_signature(signature, payload, WEBHOOK_SECRET):
        return "Unauthorized", 401

    # Perform git pull
    repo_dir = "/home/calliope/TheRizzler"
    os.chdir(repo_dir)
    subprocess.run(["git", "pull"])

    # Restart the service
    subprocess.run(["sudo", "systemctl", "restart", SERVICE_NAME])

    return "OK", 200

def verify_signature(signature, payload, secret):
    mac = hmac.new(secret.encode(), payload, "sha256")
    expected_signature = f"sha256={mac.hexdigest()}"

    return hmac.compare_digest(expected_signature, signature)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
