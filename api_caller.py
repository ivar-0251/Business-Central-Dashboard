#################################
# .env initialization
#################################

from dotenv import load_dotenv
from os import environ as env

load_dotenv()

#################################
# imports
#################################

# local import

from accesstoken import get_access_token
from get_calendar import fetch_and_save_calendars

# external imports

import requests
import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path


#################################
# variables
#################################

API_CLIENT_ID = env["api_client_id"]
API_CLIENT_SECRET = env["api_client_secret"]
API_TENANT_ID = env["api_tenant_id"]
API_COMPANY_ID = env["api_company_id"]
API_ENVIRONMENT = env["api_environment"]

AUTHORITY_URL = f"https://login.microsoftonline.com/{API_TENANT_ID}"
SCOPES = ["https://api.businesscentral.dynamics.com/.default"]

api_base_url = f"https://api.businesscentral.dynamics.com/v2.0/{API_TENANT_ID}/{API_ENVIRONMENT}"

odata_salesHeaders_url = f"{api_base_url}/api/schipper/verver/v1.0/companies({API_COMPANY_ID})/salesHeaders"

OUTPUT_FILE = Path(__file__).with_name("salesHeaders.json")


def get_delivery_week_numbers():
	today = date.today()
	return [
		(today + timedelta(weeks=week_offset)).isocalendar().week
		for week_offset in range(-1, 9)
	]


def build_delivery_week_filter(week_filter):
	week_numbers = week_filter
	if isinstance(week_numbers, int):
		week_numbers = [week_numbers]
	if not week_numbers:
		raise ValueError("Geef minimaal één deliveryWeekNo op")
	if not all(isinstance(week_number, int) for week_number in week_numbers):
		raise ValueError("deliveryWeekNo moet uit gehele getallen bestaan")

	conditions = [f"deliveryWeekNo eq {week_number}" for week_number in week_numbers]
	return conditions[0] if len(conditions) == 1 else "(" + " or ".join(conditions) + ")"


def fetch_and_save_sales_headers(week_filter=None):
	if week_filter is None:
		week_filter = get_delivery_week_numbers()

	access_token = get_access_token()
	response = requests.get(
		odata_salesHeaders_url,
		headers={"Authorization": f"Bearer {access_token}"},
		params={"$filter": build_delivery_week_filter(week_filter)},
		timeout=60,
	)
	response.raise_for_status()

	output = {
		"timestamp": datetime.now().astimezone().isoformat(),
		"data": response.json(),
	}
	OUTPUT_FILE.write_text(json.dumps(output, indent=2), encoding="utf-8")
	print(f"Sales headers opgeslagen om {output['timestamp']}")


def seconds_until_next_minute_mark(interval):
	now = time.time()
	return interval * 60 - (now % (interval * 60))


if __name__ == "__main__":
	import threading

	def update_sales_headers():
		while True:
			time.sleep(seconds_until_next_minute_mark(5))
			try:
				fetch_and_save_sales_headers()
			except Exception as error:
				print(f"Ophalen van sales headers mislukt: {error}")

	def update_calendars():
		while True:
			time.sleep(seconds_until_next_minute_mark(5))
			try:
				fetch_and_save_calendars()
			except Exception as error:
				print(f"Ophalen van agenda's mislukt: {error}")

	threading.Thread(target=update_sales_headers, daemon=True).start()
	update_calendars()