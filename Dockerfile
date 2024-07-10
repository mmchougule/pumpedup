# Use a lightweight Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create a non-root user
RUN useradd -m appuser
USER appuser

# Run both processes using supervisor
RUN pip install supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose the port your Flask app runs on
EXPOSE 5000

# Start supervisord
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]