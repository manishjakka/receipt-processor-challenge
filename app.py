import os
import socket
from flask import Flask, jsonify, request
import uuid
import math
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import psycopg2
import time

# Initialize Flask app
app = Flask(__name__)

# Configure PostgreSQL database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://flaskuser:flaskpassword@db:5432/receipts_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

@app.route('/health', methods=['GET'])
def health_check():
    try:
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

# Retry logic to wait for the database
while True:
    try:
        conn = psycopg2.connect(
            dbname="receipts_db",
            user="flaskuser",
            password="flaskpassword",
            host="db",
            port=5432
        )
        conn.close()
        print("Database connection successful.")
        break
    except psycopg2.OperationalError:
        print("Database not ready, retrying in 5 seconds...")
        time.sleep(5)

# Define Receipt model for storing in the database
class Receipt(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    retailer = db.Column(db.String(100), nullable=False)
    purchase_date = db.Column(db.String(20), nullable=False)
    purchase_time = db.Column(db.String(10), nullable=False)
    total = db.Column(db.Float, nullable=False)
    items = db.Column(db.JSON, nullable=False)
    points = db.Column(db.Integer, nullable=False)  # Store calculated points
    flask_container = db.Column(db.String(50), nullable=False)  # Flask container name
    flask_port = db.Column(db.Integer, nullable=False)  # Flask port
    request_type = db.Column(db.String(10), nullable=False)  # Type of request (GET or POST)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # Timestamp field

    def __init__(self, retailer, purchase_date, purchase_time, total, items, points, flask_container, flask_port, request_type):
        self.id = str(uuid.uuid4())
        self.retailer = retailer
        self.purchase_date = purchase_date
        self.purchase_time = purchase_time
        self.total = total
        self.items = items
        self.points = points
        self.flask_container = flask_container
        self.flask_port = flask_port
        self.request_type = request_type

# Use Flask’s `with app.app_context()` to initialize the database
with app.app_context():
    db.create_all()

# Utility function to calculate points
def calculate_points(receipt):
    points = 0

    # Rule 1: One point for every alphanumeric character in the retailer name
    retailer_name = receipt.get("retailer", "")
    points += sum(1 for c in retailer_name if c.isalnum())

    # Rule 2: 50 points if the total is a round dollar amount with no cents
    total = float(receipt.get("total", 0))
    if total.is_integer():
        points += 50

    # Rule 3: 25 points if the total is a multiple of 0.25
    if total % 0.25 == 0:
        points += 25

    # Rule 4: 5 points for every two items on the receipt
    items = receipt.get("items", [])
    points += (len(items) // 2) * 5

    # Rule 5: If the trimmed length of the item description is a multiple of 3, calculate points
    for item in items:
        description = item.get("shortDescription", "").strip()
        price = float(item.get("price", 0))
        if len(description) % 3 == 0:
            points += math.ceil(price * 0.2)

    # Rule 6: 6 points if the day in the purchase date is odd
    purchase_date = receipt.get("purchaseDate", "")
    if purchase_date:
        day = int(purchase_date.split("-")[-1])
        if day % 2 != 0:
            points += 6

    # Rule 7: 10 points if the time of purchase is after 2:00pm and before 4:00pm
    purchase_time = receipt.get("purchaseTime", "")
    if purchase_time:
        time_obj = datetime.strptime(purchase_time, "%H:%M").time()
        if datetime.strptime("14:00", "%H:%M").time() < time_obj < datetime.strptime("16:00", "%H:%M").time():
            points += 10

    return points

@app.route('/receipts/process', methods=['POST'])
def process_receipt():
    receipt_data = request.get_json()

    # Validate payload
    required_fields = ['retailer', 'purchaseDate', 'purchaseTime', 'total', 'items']
    for field in required_fields:
        if field not in receipt_data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Calculate points
    points = calculate_points({
        "retailer": receipt_data['retailer'],
        "purchaseDate": receipt_data['purchaseDate'],
        "purchaseTime": receipt_data['purchaseTime'],
        "total": str(receipt_data['total']),
        "items": receipt_data['items']
    })

    # Get the Flask container name and port
    flask_container = socket.gethostname()
    flask_port = int(os.getenv("FLASK_PORT", 5000))

    # Store in database
    receipt = Receipt(
        retailer=receipt_data['retailer'],
        purchase_date=receipt_data['purchaseDate'],
        purchase_time=receipt_data['purchaseTime'],
        total=float(receipt_data['total']),
        items=receipt_data['items'],
        points=points,
        flask_container=flask_container,
        flask_port=flask_port,
        request_type="POST"
    )
    db.session.add(receipt)
    db.session.commit()

    # Return the receipt ID and points
    return jsonify({
        "id": receipt.id
    }), 200

@app.route('/receipts/<receipt_id>/points', methods=['GET'])
def get_points(receipt_id):
    receipt = Receipt.query.get(receipt_id)

    if receipt is None:
        return jsonify({"error": "Receipt ID not found"}), 404

    # Get the Flask container name and port
    flask_container = socket.gethostname()
    flask_port = int(os.getenv("FLASK_PORT", 5000))

    # Log the GET request in the database
    log_receipt = Receipt(
        retailer=receipt.retailer,
        purchase_date=receipt.purchase_date,
        purchase_time=receipt.purchase_time,
        total=receipt.total,
        items=receipt.items,
        points=receipt.points,
        flask_container=flask_container,
        flask_port=flask_port,
        request_type="GET"
    )
    db.session.add(log_receipt)
    db.session.commit()

    return jsonify({
        "id": receipt.id,
        "points": receipt.points
    }), 200

if __name__ == '__main__':
    # Get port from environment variable or allocate a random port
    port = int(os.getenv("FLASK_PORT", 5000))
    print(f"Starting Flask app on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)
