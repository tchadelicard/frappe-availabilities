# FRAPPE – Availabilities Microservice

This is a lightweight microservice built with **Flask** to interact with Zimbra calendars over **CalDAV**. It exposes endpoints to check for available appointment slots and working-from-home days based on supervisors' calendars.

## 🧱 Tech Stack

- Python 3.10+
- Flask
- caldav (Python CalDAV client)
- Docker

## 📁 Project Structure

```
.
├── calendar_api.py       # Main Flask app
├── requirements.txt      # Python dependencies
├── Dockerfile            # Container build
└── README.md
```

## ⚙️ Setup

### Development

```bash
# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the service
python calendar_api.py
```

The API will be available at:
`http://localhost:5000`

### Environment Variables

This service does not require env vars directly but expects credentials to be passed in the body of POST requests (username, password).

## 🔌 API Endpoints

### `/slots` – Get available time slots

**Method**: `POST`
**Body**:

```json
{
  "username": "zimbra_login",
  "password": "zimbra_password",
  "date": "2025-05-02",
  "duration": "30m"
}
```

**Returns**: List of available slots with start, end, duration, and remote info.

---

### `/days` – Get available days with at least one slot

**Method**: `POST`
**Body**:

```json
{
  "username": "zimbra_login",
  "password": "zimbra_password",
  "startDate": "2025-05-01",
  "endDate": "2025-05-14",
  "duration": "30m"
}
```

**Returns**: List of dates in ISO format where a slot is available.

## 🐳 Docker

The service is containerized. To build and run:

```bash
docker build -t frappe-availabilities .
docker run -p 5000:5000 frappe-availabilities
```

Used as part of the full-stack deployment via Docker Compose (see `deployment/` repository).

## 📥 Integration

The backend Spring Boot application uses this service via the URL defined in the `FRAPPE_AVAILABILITY_API_URL` environment variable.
