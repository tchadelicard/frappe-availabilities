# Base image with Python and Alpine
FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Install necessary build packages for lxml and other dependencies
RUN apk add --no-cache gcc musl-dev libxml2 libxml2-dev libxslt libxslt-dev libffi-dev openssl-dev

# Create a non-root user and group for security
RUN addgroup -S appuser && adduser -S appuser -G appuser

# Set environment variables for Flask and Gunicorn
ENV FLASK_APP=calendar_api.py
ENV FLASK_ENV=production

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY calendar_api.py .

# Change ownership to the non-root user
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Expose the port that the Flask app runs on
EXPOSE 5000

# Run the application using Gunicorn with recommended settings
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "calendar_api:app"]