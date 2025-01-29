# Use an Ubuntu-based image
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt && \
    apt-get update && apt-get install -y curl && \
    apt-get clean && echo "Curl installed successfully"

# Copy the application code into the container
COPY . .

# Expose the Flask app's port (dynamic ports assigned at runtime)
EXPOSE 5000

# Run the Flask application
CMD ["python3", "app.py"]
