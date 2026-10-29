from os import environ as env
from dotenv import load_dotenv
load_dotenv()

import requests
from datetime import date, datetime, time, timedelta
import json
from pathlib import Path
from time import monotonic
from zoneinfo import ZoneInfo
from _acces_token_calendar import get_access_token

_CACHE_TTL_SECONDS = 60
_events_cache = {}
CALENDAR_DATA_FILE = Path(__file__).with_name('calendar.json')
DUTCH_TIMEZONE = ZoneInfo('Europe/Amsterdam')
GRAPH_DUTCH_TIMEZONE = 'W. Europe Standard Time'
CALENDAR_MAILBOXES = {
    'algemeen': 'mailbox_calendar_algemeen',
    'planning': 'mailbox_calendar_planning',
}


def get_calendar_events(week_start=None, calendar_name='algemeen'):
    if calendar_name not in CALENDAR_MAILBOXES:
        raise ValueError(f'Onbekende agenda: {calendar_name}')

    try:
        with CALENDAR_DATA_FILE.open('r', encoding='utf-8') as input_file:
            payload = json.load(input_file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    if week_start is None:
        today = datetime.now(DUTCH_TIMEZONE).date()
        week_start = today - timedelta(days=today.weekday())

    cache_key = (calendar_name, week_start, payload.get('timestamp'))
    cached = _events_cache.get(cache_key)
    if cached and monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    events = []
    for event in payload.get('calendars', {}).get(calendar_name, []):
        _normalise_event_timezone(event)
        if _event_overlaps_week(event, week_start):
            events.append(event)
    _events_cache[cache_key] = (monotonic(), events)
    return events


def _event_overlaps_week(event, week_start):
    start_text = event.get('start', {}).get('dateTime', '')
    end_text = event.get('end', {}).get('dateTime', '')
    try:
        event_start = date.fromisoformat(start_text[:10])
        event_end = date.fromisoformat(end_text[:10])
    except ValueError:
        return False

    week_end = week_start + timedelta(days=7)
    return event_start < week_end and event_end >= week_start


def _normalise_event_timezone(event):
    """Convert timed Graph values to Dutch local time, including DST."""
    for boundary in ('start', 'end'):
        boundary_data = event.get(boundary)
        if not boundary_data:
            continue

        value = boundary_data.get('dateTime', '')
        if event.get('isAllDay'):
            boundary_data['dateTime'] = f'{value[:10]}T00:00:00'
            continue

        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            continue

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=DUTCH_TIMEZONE)
        parsed = parsed.astimezone(DUTCH_TIMEZONE).replace(tzinfo=None)
        boundary_data['dateTime'] = parsed.isoformat(timespec='seconds')
        boundary_data['timeZone'] = 'Europe/Amsterdam'


def fetch_and_save_calendars():
    """Fetch both calendars for the rolling five-week window and cache them."""
    token = get_access_token()
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Prefer': f'outlook.timezone="{GRAPH_DUTCH_TIMEZONE}"',
    }
    today = datetime.now(DUTCH_TIMEZONE).date()
    start = datetime.combine(
        today - timedelta(weeks=5), time.min, tzinfo=DUTCH_TIMEZONE
    ).isoformat()
    end = datetime.combine(
        today + timedelta(weeks=5) + timedelta(days=1),
        time.min,
        tzinfo=DUTCH_TIMEZONE,
    ).isoformat()
    calendars = {}

    for calendar_name, mailbox_key in CALENDAR_MAILBOXES.items():
        calendars[calendar_name] = _fetch_calendar_events(
            env[mailbox_key], start, end, headers
        )

    payload = {
        'timestamp': datetime.now().astimezone().isoformat(),
        'range': {'start': start, 'end': end},
        'calendars': calendars,
    }
    CALENDAR_DATA_FILE.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(f"Agenda's opgeslagen om {payload['timestamp']}")


def _fetch_calendar_events(mailbox, start, end, headers):

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