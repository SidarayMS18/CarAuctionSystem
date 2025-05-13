# Start from a secure, minimal Python base image
FROM python:3.9-alpine

# Install necessary dependencies
RUN apk update && apk add --no-cache gcc libffi-dev musl-dev

# Set the working directory inside the container
WORKDIR /app

# Copy the current project files into the container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (e.g., Flask runs on port 5000)
EXPOSE 5000

# Run the app (adjust as necessary for your project)
CMD ["python", "app.py"]
