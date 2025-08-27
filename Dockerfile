FROM python:3.9-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create directory for database
RUN mkdir -p /app/data

# Expose port (if needed for future web interface)
EXPOSE 8000

# Initialize database and then keep container running
CMD ["sh", "-c", "python init_db.py && python -c \"print('Container is ready. Use docker exec to run CLI commands.')\" && tail -f /dev/null"]
