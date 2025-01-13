from flask import Flask, jsonify, request
from caldav import DAVClient
from datetime import datetime, timedelta, timezone, date
from calendar import monthrange

app = Flask(__name__)

# Hardcoded CalDAV URL
CALDAV_URL = "https://z.imt.fr/dav/{}/Calendar"  # Replace with your CalDAV server URL


# Helper function to check if a slot is free
def is_slot_free(slot_start, slot_end, events):
    for event in events:
        event_start = getattr(event.vobject_instance.vevent.dtstart, "value", None)
        event_end = getattr(event.vobject_instance.vevent.dtend, "value", None)
        summary = getattr(event.vobject_instance.vevent.summary, "value", "").lower()

        # Skip invalid or missing event times
        if event_start is None or event_end is None:
            continue

        # Convert datetime.datetime to datetime.date for all-day events
        if isinstance(event_start, datetime):
            event_start_date = event_start.date()
        else:
            event_start_date = event_start
        if isinstance(event_end, datetime):
            event_end_date = event_end.date()
        else:
            event_end_date = event_end

        # Handle all-day events
        if isinstance(event_start_date, date) and isinstance(event_end_date, date):
            # Skip "Working from home" events; they shouldn't block slots
            if "working from home" in summary:
                continue

            # Block slots for all other all-day events
            if (
                slot_start.date() >= event_start_date
                and slot_start.date() < event_end_date
            ):
                return False
        elif isinstance(event_start, datetime) and isinstance(event_end, datetime):
            # Time-based event
            if not (slot_end <= event_start or slot_start >= event_end):
                return False
    return True


# Check if the day has a "Working from home" event
def is_remote_day(events, day_date):
    for event in events:
        event_start = getattr(event.vobject_instance.vevent.dtstart, "value", None)
        event_end = getattr(event.vobject_instance.vevent.dtend, "value", None)
        summary = getattr(event.vobject_instance.vevent.summary, "value", "").lower()

        # Skip invalid or missing event times
        if event_start is None or event_end is None:
            continue

        # Convert datetime.datetime to datetime.date for all-day events
        if isinstance(event_start, datetime):
            event_start = event_start.date()
        if isinstance(event_end, datetime):
            event_end = event_end.date()

        # Check if the event is all-day and matches "Working from home"
        if isinstance(event_start, date) and isinstance(event_end, date):
            if event_start <= day_date < event_end and "working from home" in summary:
                return True

    return False


# Fetch events from all calendars
def fetch_all_events(username, password, start_time, end_time):
    client = DAVClient(
        CALDAV_URL.format(username), username=username, password=password
    )
    principal = client.principal()
    calendars = principal.calendars()
    if not calendars:
        return []

    all_events = []
    for calendar in calendars:
        events = calendar.date_search(start=start_time, end=end_time)
        all_events.extend(events)

    return all_events


@app.route("/slots", methods=["POST"])
def get_slots_for_day():
    try:
        # Get credentials, date, and duration from request body
        data = request.json
        username = data.get("username")
        password = data.get("password")
        date_str = data.get("date")  # Format: YYYY-MM-DD
        duration = data.get("duration", "30m")

        if not all([username, password, date_str]):
            return jsonify({"error": "Missing username, password, or date"}), 400

        try:
            start_time = datetime.strptime(date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

        # Exclude weekends
        if start_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return jsonify([])

        end_time = start_time + timedelta(days=1)

        # Fetch events for all calendars
        events = fetch_all_events(username, password, start_time, end_time)

        # Determine if the day is remote
        day_is_remote = is_remote_day(events, start_time.date())

        # Fetch slots for the given day
        slots = []
        day_start = datetime.combine(
            start_time.date(), datetime.min.time(), tzinfo=timezone.utc
        ) + timedelta(hours=9)
        day_end = datetime.combine(
            start_time.date(), datetime.min.time(), tzinfo=timezone.utc
        ) + timedelta(hours=17)

        slot_start = day_start
        while slot_start + timedelta(minutes=30) <= day_end:
            slot_end = slot_start + timedelta(minutes=30 if duration == "30m" else 60)

            # Check if the slot is free
            if slot_end <= day_end and is_slot_free(slot_start, slot_end, events):
                slots.append(
                    {
                        "start": slot_start.isoformat(),
                        "end": slot_end.isoformat(),
                        "duration": f"{30 if duration == '30m' else 60} minutes",
                        "remote": day_is_remote,  # Add remote status
                    }
                )

            slot_start += timedelta(minutes=30)

        return jsonify(slots)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/days", methods=["POST"])
def get_days_with_slots():
    try:
        # Get credentials and duration from request body
        data = request.json
        username = data.get("username")
        password = data.get("password")
        duration = data.get("duration", "30m")
        start_date_str = data.get("startDate")  # Format: YYYY-MM-DD
        end_date_str = data.get("endDate")  # Format: YYYY-MM-DD
        days = []

        if not all([username, password, start_date_str, end_date_str]):
            return (
                jsonify({"error": "Missing username, password, startDate, or endDate"}),
                400,
            )

        try:
            # Parse startDate and endDate
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

        # Get today's date
        today = datetime.now(timezone.utc).date()

        # Validate date ranges
        if start_date < today:
            return (
                jsonify({"error": "startDate must be greater than or equal to today."}),
                400,
            )
        if end_date < start_date + timedelta(days=1):
            return (
                jsonify({"error": "endDate must be at least 1 day after startDate."}),
                400,
            )

        current_day = start_date

        while current_day <= end_date:
            # Exclude weekends
            if current_day.weekday() >= 5:  # Saturday = 5, Sunday = 6
                current_day += timedelta(days=1)
                continue

            start_time = datetime.combine(
                current_day, datetime.min.time(), tzinfo=timezone.utc
            )
            end_of_day = start_time + timedelta(days=1)

            # Fetch events for all calendars
            events = fetch_all_events(username, password, start_time, end_of_day)

            # Check if the day has at least one available slot
            day_start = datetime.combine(
                current_day, datetime.min.time(), tzinfo=timezone.utc
            ) + timedelta(hours=9)
            day_end = datetime.combine(
                current_day, datetime.min.time(), tzinfo=timezone.utc
            ) + timedelta(hours=17)

            slot_start = day_start
            while slot_start + timedelta(minutes=30) <= day_end:
                slot_end = slot_start + timedelta(
                    minutes=30 if duration == "30m" else 60
                )

                if slot_end <= day_end and is_slot_free(slot_start, slot_end, events):
                    days.append(current_day.isoformat())
                    break

                slot_start += timedelta(minutes=30)

            current_day += timedelta(days=1)

        return jsonify(days)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
