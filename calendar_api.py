from flask import Flask, jsonify , request
from caldav import DAVClient
from datetime import datetime, timedelta, timezone

app = Flask(__name__)

# CalDAV configuration
USERNAME = "..........@imt-atlantique.net"  # Replace with your username
PASSWORD = ".........."  # Replace with your password
CALDAV_URL = (
    f"https://z.imt.fr/dav/{USERNAME}/Calendar"  # Replace with your CalDAV server URL
)

# Define working hours
WORKDAY_START = 9  # 9 AM
WORKDAY_END = 17  # 5 PM


# Function to fetch available 30-minute and 1-hour slots
def get_availabilities(duration,start_time, end_time):
    client = DAVClient(CALDAV_URL, username=USERNAME, password=PASSWORD)
    principal = client.principal()
    calendars = principal.calendars()
    if not calendars:
        return []

    # Get the primary calendar
    calendar = calendars[0]

    # Set the start time to midnight of the next day
    
   # start_time = datetime.combine(now, datetime.min.time(), tzinfo=timezone.utc)
    # end_time = start_time + timedelta(days=7)  # Timeframe: Next 7 days

    # Fetch events in the specified timeframe
    events = calendar.date_search(start=start_time, end=end_time)
    available_slots = []
    current_day = start_time.date()

    while current_day <= end_time.date():
        day_start = datetime.combine(current_day, datetime.min.time(), tzinfo=timezone.utc) + timedelta(
            hours=WORKDAY_START
        )
        day_end = datetime.combine(current_day, datetime.min.time(), tzinfo=timezone.utc) + timedelta(
            hours=WORKDAY_END
        )

        # Generate all possible slots within work hours
        slot_start = day_start
        while slot_start + timedelta(minutes=30) <= day_end:
            # Generate 30-minute slot
            slot_30_end = slot_start + timedelta(minutes=30)
            # Generate 1-hour slot
            slot_60_end = slot_start + timedelta(minutes=60)

            # Check if the 30-minute slot is free
            if duration == "30m" and is_slot_free(slot_start, slot_30_end, events):
                available_slots.append(
                    {
                        "start": slot_start.isoformat(),
                        "end": slot_30_end.isoformat(),
                        "duration": "30 minutes",
                    }
                )
            # Check if the 1-hour slot is free and within the day bounds
            if duration == "60m" and slot_60_end <= day_end and is_slot_free(slot_start, slot_60_end, events):
                available_slots.append(
                    {
                        "start": slot_start.isoformat(),
                        "end": slot_60_end.isoformat(),
                        "duration": "1 hour",
                    }
                )
           

            slot_start += timedelta(minutes=30)  # Move to the next 30-minute interval

        current_day += timedelta(days=1)

    return available_slots

# Helper function to check if a slot is free
def is_slot_free(slot_start, slot_end, events):
    for event in events:
        event_start = event.vobject_instance.vevent.dtstart.value
        event_end = event.vobject_instance.vevent.dtend.value
       
        # Convert event_start and event_end to timezone-aware datetimes if needed
        if isinstance(event_start, datetime) and event_start.tzinfo is None:
            event_start = event_start.replace(tzinfo=timezone.utc)
        if isinstance(event_end, datetime) and event_end.tzinfo is None:
            event_end = event_end.replace(tzinfo=timezone.utc)

        # Ensure datetime comparison
        if not (slot_end <= event_start or slot_start >= event_end):
            return False
    return True

# API endpoint
@app.route("/availabilities", methods=["GET"]) 
def Availabilities():
    try:
        now = datetime.now(timezone.utc)
        start_time = datetime.combine(now, datetime.min.time(), tzinfo=timezone.utc)
        end_time = start_time + timedelta(days=7)  # Timeframe: Next 7 days
        duration = request.args.get('duration', default='30m')
        data = get_availabilities(duration, start_time, end_time)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/dailyavailabilities", methods=["GET"]) 
def DailyAvailabilities():
    try:
        now = datetime.now(timezone.utc)
        start = request.args.get('date', default='2023-10-01')
        try:
        # Convertir 'start' en un objet datetime avec un fuseau horaire UTC
            start_time = datetime.strptime(start, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

        end_time = start_time
        duration = request.args.get('duration', default='30m')
        data = get_availabilities(duration, start_time, end_time)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
