from os import environ as env
from dotenv import load_dotenv
load_dotenv()

import requests
from datetime import datetime, timedelta
from _acces_token_calendar import get_access_token

def get_calendar_events():
    token = get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    mailbox = env["mailbox_calendar"]
    now = datetime.now()
    start_of_week = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    start = start_of_week.isoformat()
    end = (now + timedelta(days=14)).isoformat()
    print(f"Fetching events from {start} ({datetime.now()}) to {end} ({datetime.now() + timedelta(days=14)}) for mailbox {mailbox}")

    url = f"https://graph.microsoft.com/v1.0/users/{mailbox}/calendarview"
    params = {
        "startDateTime": start,
        "endDateTime": end,
        "$orderby": "start/dateTime",
    }

    events = []
    while url:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        events.extend(data["value"])
        url = data.get("@odata.nextLink")
        params = None

    return events