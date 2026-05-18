"""
Quick local test: list this week's meetings from Outlook desktop via COM.

Requires:
    pip install pywin32
    Outlook desktop installed and configured.

Just run:
    python test_outlook_calendar.py
"""

import datetime
import sys

DAYS_AHEAD = 7
INCLUDE_BODY = True

try:
    import win32com.client
    import pythoncom
except ImportError:
    sys.exit("pywin32 not installed. Run: pip install pywin32")

pythoncom.CoInitialize()

try:
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
except Exception as e:
    sys.exit(f"Cannot connect to Outlook (installed and running?): {e}")

# --- Diagnostic: list all available accounts/stores ---
print("=== Accounts/Stores detected ===")
for i, store in enumerate(outlook.Stores, 1):
    print(f"  [{i}] {store.DisplayName}  (type={store.ExchangeStoreType})")
print()

# Default calendar (account principal Outlook)
calendar = outlook.GetDefaultFolder(9)  # 9 = olFolderCalendar
print(f"Default calendar folder: '{calendar.Name}' on store '{calendar.Store.DisplayName}'")
print(f"Total items in default calendar (unfiltered): {calendar.Items.Count}")
print()

items = calendar.Items
# Correct order: Sort FIRST, then IncludeRecurrences (Outlook quirk)
items.Sort("[Start]")
items.IncludeRecurrences = True

now = datetime.datetime.now()
week_end = now + datetime.timedelta(days=DAYS_AHEAD)

print(f"Fetching meetings between {now:%Y-%m-%d %H:%M} and {week_end:%Y-%m-%d %H:%M}...\n")

# Manual iteration (more reliable than Restrict on FR-locale Windows)
count = 0
for item in items:
    try:
        # item.Start is a pywintypes datetime
        start = item.Start
        # Convert to naive datetime for comparison
        start_dt = datetime.datetime(
            start.year, start.month, start.day,
            start.hour, start.minute, start.second
        )

        if start_dt < now:
            continue
        if start_dt > week_end:
            # Items are sorted ascending, so we can stop
            break

        count += 1
        attendees = [r.Name for r in item.Recipients] if item.Recipients else []

        print(f"--- Meeting {count} ---")
        print(f"  Subject   : {item.Subject or '(no subject)'}")
        print(f"  Start     : {item.Start}")
        print(f"  End       : {item.End}")
        print(f"  Organizer : {item.Organizer or '(unknown)'}")
        if item.Location:
            print(f"  Location  : {item.Location}")
        if attendees:
            print(f"  Attendees : {', '.join(attendees)}")
        if INCLUDE_BODY and item.Body:
            body = item.Body.strip().replace("\r", " ").replace("\n", " ")
            print(f"  Body      : {body[:300]}...")
        print()
    except Exception as e:
        print(f"  [warn] could not read item: {e}", file=sys.stderr)

if count == 0:
    print("No upcoming meetings found in this window.")
    print()
    print("Possible reasons:")
    print(" - Your meetings are on a different account/store (see list above)")
    print(" - Outlook is not synced — open Outlook desktop and let it sync first")
    print(" - You only use web Outlook (Teams/M365 web) — desktop client required")
else:
    print(f"Total: {count} meeting(s)")
