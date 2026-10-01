from os import environ as env
from dotenv import load_dotenv
load_dotenv()

import requests
from datetime import date, datetime, timedelta
from time import monotonic
from _acces_token_calendar import get_access_token

_CACHE_TTL_SECONDS = 60
_events_cache = {}


def get_calendar_events(week_start=None):
    if week_start is None:
        week_start = date.today() - timedelta(days=date.today().weekday())

    cached = _events_cache.get(week_start)
    if cached and monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    events = _fetch_calendar_events(week_start)
    _events_cache[week_start] = (monotonic(), events)
    return events


def _fetch_calendar_events(week_start):

    token = get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    mailbox = env["mailbox_calendar"]
    start = datetime.combine(week_start, datetime.min.time()).isoformat()
    end = datetime.combine(week_start + timedelta(days=7), datetime.min.time()).isoformat()
    print(f"Fetching events from {start} to {end} for mailbox {mailbox}")

    url = f"https://graph.microsoft.com/v1.0/users/{mailbox}/calendarview"
    params = {
        "startDateTime": start,
        "endDateTime": end,
        "$orderby": "start/dateTime",
        "$select": "subject,start,end,isAllDay,location",
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