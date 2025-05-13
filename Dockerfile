FROM python:3.9-slim

# Create and set the working directory
WORKDIR /app

# Copy all project files into the container's /app directory
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Flask runs on
EXPOSE 5000

# Start the app
CMD ["python", "app.py"]
