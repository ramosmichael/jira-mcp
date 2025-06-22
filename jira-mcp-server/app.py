from flask import Flask, redirect, request, jsonify
import requests
import os
from config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, AUTH_URL, TOKEN_URL, RESOURCE_URL

app = Flask(__name__)

@app.route("/")
def home():
    return f"""
    <h2>Connect Jira via Atlassian OAuth</h2>
    <a href="/auth">Click here to authorize</a>
    """

@app.route("/auth")
def auth():
    scopes = "read:jira-user read:jira-work write:jira-work"
    url = (
        f"{AUTH_URL}?audience=api.atlassian.com&client_id={CLIENT_ID}"
        f"&scope={scopes}&redirect_uri={REDIRECT_URI}&response_type=code&prompt=consent"
    )
    return redirect(url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "No code provided", 400

    # Step 1: Exchange code for access token
    token_response = requests.post(
        TOKEN_URL,
        json={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Content-Type": "application/json"},
    )

    token_data = token_response.json()
    access_token = token_data.get("access_token")
    if not access_token:
        return jsonify(token_data), 500

    # Step 2: Get accessible Jira resources
    resource_response = requests.get(
        RESOURCE_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    resources = resource_response.json()

    return jsonify({
        "access_token": access_token,
        "resources": resources
    })

@app.route("/api/mcp", methods=["POST"])
def mcp_entry():
    # Here you would handle messages or events sent to your MCP-style server
    data = request.json
    print("Received MCP payload:", data)
    return jsonify({"status": "received"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)