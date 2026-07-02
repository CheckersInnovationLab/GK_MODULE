FROM python:3.11-slim

# Set working directory to /code
WORKDIR /code

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app contents into /code/app to preserve Python module structure
COPY . /code/app

# Expose the port
EXPOSE 8011

# Run the FastAPI application on port 8011
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8011"]
