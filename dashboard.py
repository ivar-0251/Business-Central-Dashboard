#######################################
# Business Central API Connection
#######################################


from dotenv import load_dotenv
from os import environ as env
from datetime import date, datetime, timedelta
from pathlib import Path
import pandas as pd
import json
import re
from urllib.parse import quote
from get_calendar import get_calendar_events

load_dotenv()  # Load environment variables from .env file

#######################################
# Functions
#######################################

def get_calendar_event_color(event):
    """Classify a calendar event by its subject.

    **Parameters:**
    - `event`: Calendar event dictionary containing a `subject` value.

    **Returns:** The CSS class name used to display the event.
    """
    subject = event.get('subject', '')
    has_word = lambda word: re.search(rf'\b{word}\b', subject, re.IGNORECASE)
    has_word_pair = lambda first, second: re.search(
        rf'\b{first}(?:[\s-]+{second}|{second})\b',
        subject,
        re.IGNORECASE,
    )

    if has_word('vrij') or has_word('vakantie'):
        return 'calendar-event-free'
    if has_word('kantoor') or has_word('kantoordag') or has_word_pair('kantoor', 'dag'):
        return 'calendar-event-office'
    if (has_word('niet') and has_word('werkdag')) or has_word_pair('niet', 'werkdag'):
        return 'calendar-event-not-working'
    if (has_word('thuis') and has_word('werkdag')) or has_word_pair('thuis', 'werkdag') or (has_word('thuis') and has_word('werken')) or has_word_pair('thuis', 'werken'):
        return 'calendar-event-home-working'
    return 'calendar-event-other'


def get_calendar_event_sort_key(event):
    """Build the sort key for a calendar event.

    **Parameters:**
    - `event`: Calendar event dictionary with `color_class` and optional start data.

    **Returns:** A tuple that sorts events by category and start time.
    """
    color_order = {
        'calendar-event-office': 0,
        'calendar-event-home-working': 1,
        'calendar-event-not-working': 2,
        'calendar-event-other': 3,
    }
    return (
        color_order[event['color_class']],
        event.get('start', {}).get('dateTime', ''),
    )


def sort_calendar_events(events):
    """Sort normal calendar events while preserving free events in place.

    **Parameters:**
    - `events`: Iterable of calendar event dictionaries.

    **Returns:** A list with sortable events ordered by category and start time.
    """
    sortable_events = sorted(
        (event for event in events if event['color_class'] != 'calendar-event-free'),
        key=get_calendar_event_sort_key,
    )
    sortable_events = iter(sortable_events)
    return [
        event if event['color_class'] == 'calendar-event-free' else next(sortable_events)
        for event in events
    ]

def bereken_ordertypes(week_orders):
    """Count main, accompanying, and standalone orders for one week.

    **Parameters:**
    - `week_orders`: Pandas DataFrame containing order and main-order columns.

    **Returns:** A dictionary with counts for each order type.
    """
    if 'Nr.' not in week_orders or 'Hoofdorder' not in week_orders:
        return {
            'hoofdorders': 0,
            'meeliftorders': 0,
            'losstaande_orders': 0,
        }

    heeft_hoofdorder = (
        week_orders['Hoofdorder'].notna()
        & week_orders['Hoofdorder'].astype('string').str.strip().ne('')
    )
    is_hoofdorder = heeft_hoofdorder & week_orders['Nr.'].eq(week_orders['Hoofdorder'])

    return {
        'hoofdorders': int(is_hoofdorder.sum()),
        'meeliftorders': int((heeft_hoofdorder & ~is_hoofdorder).sum()),
        'losstaande_orders': int((~heeft_hoofdorder).sum()),
    }

#######################################
# Flask Application
#######################################

from flask import Flask, abort, render_template, redirect, request, url_for

app = Flask(__name__)
API_DATA_FILE = Path(__file__).with_name('salesHeaders.json')


def business_central_order_url(order_number):
    """Build a link to an order in Business Central.

    **Parameters:**
    - `order_number`: The order number used in the Business Central filter.

    **Returns:** A URL that opens page 42 filtered to the given order.
    """
    base_url = (
        f"https://businesscentral.dynamics.com/{env['api_tenant_id']}"
        f"/{env['api_environment']}"
    )
    company = quote(env.get('api_company_name', 'Verver Export B.V.'), safe='')
    order_filter = quote(f"'No.' IS '{order_number}'", safe="'")
    return f"{base_url}?company={company}&page=42&filter={order_filter}"


@app.context_processor
def inject_business_central_helpers():
    """Expose Business Central URL helpers to all Jinja templates.

    **Parameters:** None.

    **Returns:** A template context dictionary containing the order URL helper.
    """
    return {'business_central_order_url': business_central_order_url}


def load_dashboard_data():
    """Load cached Business Central data and calculate dashboard summaries.

    **Parameters:** None.

    **Returns:** A tuple containing dashboard data and its last-updated timestamp.
    """
    try:
        with API_DATA_FILE.open('r', encoding='utf-8') as input_file:
            payload = json.load(input_file)
    except (FileNotFoundError, json.JSONDecodeError):
        abort(503, description='De API-data is niet beschikbaar.')

    orders = [
        {
            'Status': order.get('status'),
            'Leverweek': order.get('deliveryWeekNo'),
            'Aantal kratten': order.get('crateQuantity') or 0,
            'Nr.': order.get('no'),
            'Naam': order.get('sellToCustomerName'),
            'Hoofdorder': order.get('mainOrderNo') or None,
            'Verzonden': order.get('shipped', False),
            'Mag. Verzending bestaat.': order.get('whseShipmentExists', False),
        }
        for order in payload.get('data', {}).get('value', [])
    ]

    orders_df = pd.DataFrame(orders)
    orders_df['Leverweek'] = pd.to_numeric(orders_df['Leverweek'], errors='coerce')
    orders_df['Aantal kratten'] = pd.to_numeric(
        orders_df['Aantal kratten'], errors='coerce'
    ).fillna(0)

    huidige_week = date.today().isocalendar().week
    komende_weken = sorted(
        int(week)
        for week in orders_df.loc[
            orders_df['Leverweek'] >= huidige_week, 'Leverweek'
        ].dropna().unique()
    )

    weekgegevens = []
    for week in komende_weken:
        week_orders = orders_df.loc[orders_df['Leverweek'] == week]
        orders_count = len(week_orders)
        colli = week_orders['Aantal kratten'].sum()
        colli = colli.item() if hasattr(colli, 'item') else colli
        frequentie = week_orders['Aantal kratten'].value_counts().sort_index()

        weekgegevens.append({
            'week': week,
            'orders': orders_count,
            'colli': colli,
            'gemiddelde': round(float(colli) / orders_count, 1) if orders_count else 0,
            **bereken_ordertypes(week_orders),
            'frequentie': [
                {
                    'aantal_kratten': int(aantal_kratten),
                    'aantal_orders': int(aantal_orders),
                }
                for aantal_kratten, aantal_orders in frequentie.items()
            ],
            'orderkolommen': ['Aantal kratten'],
        })

    timestamp = datetime.fromisoformat(payload['timestamp'])
    last_updated = timestamp.strftime('%d-%m-%Y %H:%M')
    return {'weekgegevens': weekgegevens, 'orders': orders}, last_updated

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    data, last_updated = load_dashboard_data()

    return render_template(
        'dashboard.html',
        data=data,
        current_week=date.today().isocalendar().week,
        last_updated=last_updated,
    )


@app.route('/dashboard/week-<int:weeknummer>')
def week_overview(weeknummer):
    data, last_updated = load_dashboard_data()

    weekgegevens = next(
        (week for week in data.get('weekgegevens', []) if week['week'] == weeknummer),
        None,
    )
    if weekgegevens is None:
        abort(404)

    week_orders = [
        order for order in data.get('orders', [])
        if str(order.get('Leverweek', '')).strip() == str(weeknummer)
    ]
    order_columns = list(dict.fromkeys(
        column for order in week_orders for column in order.keys()
    ))

    return render_template(
        'week_overview.html',
        week=weekgegevens,
        orders=week_orders,
        order_columns=order_columns,
        last_updated=last_updated,
    )


@app.route('/dashboard/hoofdorders/<int:weeknummer>')
def hoofdorders(weeknummer):
    data, last_updated = load_dashboard_data()

    orders_df = pd.DataFrame(data.get('orders', []))
    required_columns = {'Leverweek', 'Nr.', 'Naam', 'Hoofdorder', 'Aantal kratten'}
    if not required_columns.issubset(orders_df.columns):
        abort(404)

    orders_df['Leverweek'] = pd.to_numeric(orders_df['Leverweek'], errors='coerce')
    orders_df['Nr.'] = pd.to_numeric(orders_df['Nr.'], errors='coerce')
    orders_df['Hoofdorder'] = pd.to_numeric(orders_df['Hoofdorder'], errors='coerce')
    orders_df['Aantal kratten'] = pd.to_numeric(
        orders_df['Aantal kratten'], errors='coerce'
    ).fillna(0)
    week_orders = orders_df.loc[orders_df['Leverweek'] == weeknummer]
    heeft_hoofdorder = week_orders['Hoofdorder'].notna()
    hoofdorder_rows = week_orders.loc[
        heeft_hoofdorder & week_orders['Nr.'].eq(week_orders['Hoofdorder'])
    ]

    ordergroepen = []
    for _, hoofdorder in hoofdorder_rows.iterrows():
        meeliftorders = week_orders.loc[
            heeft_hoofdorder
            & week_orders['Hoofdorder'].eq(hoofdorder['Nr.'])
            & week_orders['Nr.'].ne(hoofdorder['Nr.'])
        ]
        ordergroepen.append({
            'nummer': int(hoofdorder['Nr.']),
            'naam': hoofdorder['Naam'],
            'colli': hoofdorder['Aantal kratten'] + meeliftorders['Aantal kratten'].sum(),
            'meeliftorders': [
                {'nummer': int(order['Nr.']), 'naam': order['Naam']}
                for _, order in meeliftorders.iterrows()
            ],
        })

    return render_template(
        'hoofdorders.html',
        weeknummer=weeknummer,
        ordergroepen=ordergroepen,
        totaal_meeliftorders=sum(
            len(ordergroep['meeliftorders']) for ordergroep in ordergroepen
        ),
        last_updated=last_updated,
    )

@app.route('/verzendingen')
def verzendingen():
    data, last_updated = load_dashboard_data()

    return render_template(
        'verzendingen.html',
        data=data,
        current_week=date.today().isocalendar().week,
        last_updated=last_updated,
    )

@app.route('/kiosk/display-1')
def kiosk_display_1():
    data, last_updated = load_dashboard_data()

    return render_template(
        'kiosk_display_1.html',
        data=data,
        current_week=date.today().isocalendar().week,
        last_updated=last_updated,
    )

@app.route('/kiosk/display-2')
def kiosk_display_2():
    data, last_updated = load_dashboard_data()

    return render_template(
        'kiosk_display_2.html',
        data=data,
        current_week=date.today().isocalendar().week,
        last_updated=last_updated,
    )

def load_calendar_view_data(week_offset=0, calendar_name='algemeen'):
    """Load and group calendar events for a selected work week.

    **Parameters:**
    - `week_offset`: Number of weeks relative to the current week.

    **Returns:** A tuple containing calendar days and spanning events.
    """
    today = date.today()
    week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=5)
    weekday_names = [
        'Maandag', 'Dinsdag', 'Woensdag', 'Donderdag',
        'Vrijdag', 'Zaterdag', 'Zondag',
    ]
    events_by_date = {week_start + timedelta(days=offset): [] for offset in range(5)}
    spanning_events = []

    for event in get_calendar_events(week_start, calendar_name):
        event['color_class'] = get_calendar_event_color(event)
        start_text = event.get('start', {}).get('dateTime', '')
        end_text = event.get('end', {}).get('dateTime', '')
        try:
            event_start = date.fromisoformat(start_text[:10])
            event_end = date.fromisoformat(end_text[:10])
        except ValueError:
            continue

        if event.get('isAllDay'):
            event_end -= timedelta(days=1)
        if event_end < week_start or event_start >= week_end:
            continue

        display_start = max(event_start, week_start)
        display_end = min(event_end, week_end - timedelta(days=1))
        if display_start < display_end:
            event['grid_start'] = (display_start - week_start).days + 1
            event['grid_end'] = (display_end - week_start).days + 2
            spanning_events.append(event)
        else:
            events_by_date[display_start].append(event)

    for event_date, events in events_by_date.items():
        events_by_date[event_date] = sort_calendar_events(events)
    spanning_events = sort_calendar_events(spanning_events)

    calendar_days = [
        {
            'date': event_date,
            'label': f'{weekday_names[event_date.weekday()]} {event_date:%d-%m}',
            'is_today': event_date == today,
            'events': events,
        }
        for event_date, events in events_by_date.items()
    ]

    return calendar_days, spanning_events


@app.route('/agenda')
def agenda():
    week_offset = request.args.get('week_offset', default=0, type=int)
    calendar_name = request.args.get('calendar', default='algemeen')
    if calendar_name not in {'algemeen', 'planning'}:
        abort(404)
    calendar_days, spanning_events = load_calendar_view_data(week_offset, calendar_name)
    selected_week = date.today() - timedelta(days=date.today().weekday()) + timedelta(weeks=week_offset)

    return render_template(
        'agenda.html',
        calendar_days=calendar_days,
        spanning_events=spanning_events,
        current_week=selected_week.isocalendar().week,
        week_offset=week_offset,
        calendar_name=calendar_name,
    )


@app.route('/kiosk/display-3')
def kiosk_display_3():
    calendar_days, spanning_events = load_calendar_view_data(calendar_name='algemeen')

    return render_template(
        'kiosk_display_3.html',
        calendar_days=calendar_days,
        spanning_events=spanning_events,
        current_week=date.today().isocalendar().week,
        calendar_name='algemeen',
    )


@app.route('/kiosk/display-4')
def kiosk_display_4():
    calendar_days, spanning_events = load_calendar_view_data(calendar_name='planning')

    return render_template(
        'kiosk_display_4.html',
        calendar_days=calendar_days,
        spanning_events=spanning_events,
        current_week=date.today().isocalendar().week,
        calendar_name='planning',
    )

if __name__ == '__main__':
    app.run(debug=True, host=env['host'], port=env['port'])
