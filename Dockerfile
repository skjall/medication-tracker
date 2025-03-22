FROM python:3.13-slim@sha256:8f3aba466a471c0ab903dbd7cb979abd4bda370b04789d25440cc90372b50e04

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

# Create a volume for data persistence
VOLUME /app/data

# Expose the port the app runs on
EXPOSE 8080

# Command to run the application
CMD ["python", "main.py"]
