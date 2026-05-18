"""
Graph API test: list this week's meetings via OAuth device code flow.
Works with BOTH classic Outlook and Nouvel Outlook (the data lives in M365 cloud).

Requires:
    pip install msal requests

Just run:
    python test_graph_calendar.py

First run: a code appears, open the URL, log in with Microsoft, paste the code.
Subsequent runs: silent (token cached locally in graph_token_cache.bin).

NOTE: The app is currently registered as SINGLE-TENANT in Azure, so only
yele.fr accounts can log in. For multi-tenant (any company), the app
registration's "Supported account types" must be switched to multi-tenant.
"""

import datetime
import json
import os
import sys

try:
    import msal
    import requests
except ImportError:
    sys.exit("Missing dependencies. Run: pip install msal requests")

# --- Config (from Azure App Registration) ---
CLIENT_ID = "12351aae-0fce-4628-8124-3f0df9e6be50"
TENANT_ID = "0922c70a-4c47-4b76-bc88-0a46299375d0"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["Calendars.Read"]
TOKEN_CACHE_FILE = "graph_token_cache.bin"

DAYS_AHEAD = 7
TIMEZONE = "Romance Standard Time"  # Paris

# --- Token cache so we don't re-login every run ---
cache = msal.SerializableTokenCache()
if os.path.exists(TOKEN_CACHE_FILE):
    with open(TOKEN_CACHE_FILE, "r") as f:
        cache.deserialize(f.read())

app = msal.PublicClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
    token_cache=cache,
)

# Try silent auth first (uses cached refresh token)
accounts = app.get_accounts()
result = None
if accounts:
    print(f"Found cached account: {accounts[0]['username']}, trying silent auth...")
    result = app.acquire_token_silent(SCOPES, account=accounts[0])

# Fall back to device code flow on first run
if not result:
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        sys.exit(f"Device flow failed to start:\n{json.dumps(flow, indent=2)}")
    print("\n" + "=" * 60)
    print(flow["message"])
    print("=" * 60 + "\n")
    print("Waiting for you to log in in the browser...")
    result = app.acquire_token_by_device_flow(flow)

if "access_token" not in result:
    sys.exit(f"Authentication failed:\n{json.dumps(result, indent=2)}")

# Persist token cache
if cache.has_state_changed:
    with open(TOKEN_CACHE_FILE, "w") as f:
        f.write(cache.serialize())

token = result["access_token"]
print("Auth OK.\n")

# --- Call Graph API ---
now = datetime.datetime.utcnow()
week_end = now + datetime.timedelta(days=DAYS_AHEAD)
start_iso = now.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
end_iso = week_end.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

# calendarView (vs /events) expands recurring meetings within the date window
url = "https://graph.microsoft.com/v1.0/me/calendarView"
params = {
    "startDateTime": start_iso,
    "endDateTime": end_iso,
    "$select": "subject,start,end,organizer,location,attendees,bodyPreview,isOnlineMeeting",
    "$orderby": "start/dateTime",
    "$top": 100,
}
headers = {
    "Authorization": f"Bearer {token}",
    "Prefer": f'outlook.timezone="{TIMEZONE}"',
}

print(f"Fetching meetings between {start_iso} and {end_iso}...\n")
resp = requests.get(url, headers=headers, params=params, timeout=30)

if resp.status_code != 200:
    sys.exit(f"Graph API error {resp.status_code}:\n{resp.text}")

events = resp.json().get("value", [])

for i, e in enumerate(events, 1):
    print(f"--- Meeting {i} ---")
    print(f"  Subject     : {e.get('subject') or '(no subject)'}")
    print(f"  Start       : {e['start']['dateTime']}  ({e['start']['timeZone']})")
    print(f"  End         : {e['end']['dateTime']}")

    organizer = e.get("organizer", {}).get("emailAddress", {})
    print(f"  Organizer   : {organizer.get('name', '?')} <{organizer.get('address', '?')}>")

    loc = (e.get("location") or {}).get("displayName")
    if loc:
        print(f"  Location    : {loc}")

    attendees = e.get("attendees", [])
    if attendees:
        names = [a["emailAddress"].get("name") or a["emailAddress"].get("address") for a in attendees]
        print(f"  Attendees   : {', '.join(names)}")

    if e.get("isOnlineMeeting"):
        print(f"  Online      : yes (Teams)")

    body = e.get("bodyPreview", "").strip()
    if body:
        body = body.replace("\r", " ").replace("\n", " ")
        print(f"  Body preview: {body[:300]}")
    print()

print(f"Total: {len(events)} meeting(s)")
if not events:
    print("(Check that you have meetings within the next 7 days and that you logged in with the right account.)")
