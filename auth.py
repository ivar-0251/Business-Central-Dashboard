from os import environ as env
import uuid, msal
from flask import Blueprint, abort, redirect, request, session, url_for


bp = Blueprint("auth", __name__)

CLIENT_ID = env["client_id_auth"]
CLIENT_SECRET = env["client_secret_auth"]
TENANT_ID = env["tentant_id_auth"]
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["User.Read"]

def build_msal_app():
    return msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )

@bp.route("/login")
def login():
    session["state"] = str(uuid.uuid4())
    url = build_msal_app().get_authorization_request_url(
        SCOPE,
        state=session["state"],
        redirect_uri="http://localhost/auth/getAToken",
    )
    return redirect(url)

@bp.route("/getAToken")
def authorized():
    if request.args.get("state") != session.get("state"):
        abort(400, "Ongeldige state")
    if "error" in request.args:
        abort(401, request.args.get("error_description", "Inloggen mislukt"))

    code = request.args.get("code")
    if not code:
        abort(400)

    result = build_msal_app().acquire_token_by_authorization_code(
        code,
        scopes=SCOPE,
        redirect_uri=url_for("auth.authorized", _external=True),
    )
    if "error" in result:
        abort(401, result.get("error_description"))

    claims = result["id_token_claims"]
    if claims.get("tid") != TENANT_ID:
        abort(403, "Geen toegang: ander Microsoft-account dan van ons bedrijf")

    session["user"] = {
        "name": claims.get("name"),
        "email": claims.get("preferred_username"),
        "oid": claims.get("oid"),
    }
    return redirect(url_for("index"))