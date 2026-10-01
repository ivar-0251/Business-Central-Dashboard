#################################
# .env initialization
#################################

from dotenv import load_dotenv
from os import environ as env

load_dotenv()

#################################
# imports
#################################

from msal import ConfidentialClientApplication

#################################
# variables
#################################

API_CLIENT_ID = env["api_client_id"]
API_CLIENT_SECRET = env["api_client_secret"]
API_TENANT_ID = env["api_tenant_id"]

AUTHORITY_URL = f"https://login.microsoftonline.com/{API_TENANT_ID}"
SCOPES = ["https://api.businesscentral.dynamics.com/.default"]

#################################
# functions
#################################

def get_access_token():

    msal_app = ConfidentialClientApplication(API_CLIENT_ID, authority=AUTHORITY_URL, client_credential=API_CLIENT_SECRET)
    result = msal_app.acquire_token_for_client(scopes=SCOPES)

    if "access_token" in result:
        access_token = result["access_token"]
        return access_token
    else:
        raise Exception("Failed to acquire access token: " + result.get("error_description", "Unknown error"))

