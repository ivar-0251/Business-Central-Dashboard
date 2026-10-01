from os import environ as env
from dotenv import load_dotenv
load_dotenv()

import msal

CLIENT_ID = env["client_id_calendar"]
TENANT_ID = env["tenant_id_calendar"]
CLIENT_SECRET = env["client_secret_calendar"]

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

app = msal.ConfidentialClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
    client_credential=CLIENT_SECRET
)

def get_access_token():
    result = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception("Failed to obtain access token: " + str(result.get("error_description", "Unknown error")))