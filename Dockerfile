# Use the official Python 3.11 image from the Docker Hub
FROM python:3.11.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    curl \
    supervisor && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install gunicorn

# Copy the rest of the application except the 'data' directory
COPY . /app

# Set up Supervisord configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose the port Flask is accessible on
EXPOSE 8573

# Start processes defined in Supervisord configuration
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
