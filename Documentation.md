# Receipt Processing System Documentation

## Overview

This project is a receipt processing system built with Docker to run multiple components in containers. **NGINX** acts as a load balancer for scaled Flask applications, which interact with a PostgreSQL database. The system is designed to efficiently process receipts, calculate points, and store request metadata for tracking and reporting purposes.

---

## System Architecture

The system consists of the following key components:

1. **NGINX Load Balancer**: 
   - Acts as the entry point to the system.
   - Distributes incoming requests among Flask containers.
   - Ensures high availability and load distribution for the Flask backend.

2. **Flask App**: 
   - A Python web application that processes and calculates points for receipts.
   - Implements endpoints for processing (`POST /receipts/process`) and querying points (`GET /receipts/<receipt_id>/points`).
   - Each Flask container communicates with the PostgreSQL database to store and retrieve data.

3. **PostgreSQL Database**:
   - Stores all receipt-related data, including retailer information, total amounts, points, and metadata such as the Flask container name, port, and request type (GET/POST).

---

## Components in Detail

### NGINX Load Balancer

- **Purpose**:
  - Acts as a reverse proxy and distributes incoming HTTP requests across multiple Flask containers.
  - Ensures scalability and fault tolerance.

- **Configuration**:
  - The NGINX configuration is defined in `nginx.conf`.
  - The load balancer dynamically resolves the Flask containers using Docker's internal DNS.
  - It includes health checks, compression, security headers, and debugging headers for backend tracing.

- **Key Features**:
  - **Load Balancing**: Balances traffic between multiple Flask containers (replicas).
  - **Health Check**: Redirects traffic only to healthy Flask containers.
  - **Debugging Header**: Adds `X-Backend-Server` to responses, showing which Flask container handled the request.

- **Port Mapping**:
  - NGINX listens on **port 80** on the host machine and forwards requests to Flask containers on their internal ports.

---

### Flask App

- **Purpose**:
  - Implements the receipt processing logic.
  - Exposes APIs for receipt processing (`POST`) and retrieving points (`GET`).

- **Endpoints**:
  1. **POST `/receipts/process`**:
     - Processes a receipt, calculates points, and stores data in the database.
     - Metadata such as the Flask container name, port, and request type are also stored.

     Example Request:
     ```json
     {
       "retailer": "Target",
       "purchaseDate": "2023-01-01",
       "purchaseTime": "13:30",
       "total": "15.00",
       "items": [
         { "shortDescription": "Mountain Dew 12PK", "price": "6.49" },
         { "shortDescription": "Doritos Nacho Cheese", "price": "3.35" }
       ]
     }
     ```

     Example Response:
     ```json
     {
       "id": "a1b2c3d4-5678-90ef-ghij-1234567890kl"
     }
     ```

  2. **GET `/receipts/<receipt_id>/points`**:
     - Fetches the points for a given receipt.
     - Logs the metadata for the GET request.

     Example Response:
     ```json
     {
       "id": "a1b2c3d4-5678-90ef-ghij-1234567890kl",
       "points": 55
     }
     ```

- **Key Features**:
  - Uses SQLAlchemy ORM to interact with the PostgreSQL database.
  - Logs metadata for both GET and POST requests (e.g., Flask container name, port, and request type).

- **Flask Metadata Logging**:
  - **`flask_container`**: Name of the container handling the request.
  - **`flask_port`**: Internal port (5000) of the container.
  - **`request_type`**: Whether the request is `GET` or `POST`.

- **Scaling**:
  - The Flask app is scaled to 3 replicas using Docker Compose.

---

### PostgreSQL Database

- **Purpose**:
  - Stores receipt data, including retailer information, total amounts, points, and metadata.

- **Schema**:
  - The `Receipt` table is defined with the following fields:
    - **id**: Unique identifier for the receipt (UUID).
    - **retailer**: Name of the retailer.
    - **purchase_date**: Date of purchase.
    - **purchase_time**: Time of purchase.
    - **total**: Total amount spent.
    - **items**: List of items in JSON format.
    - **points**: Calculated points for the receipt.
    - **flask_container**: Name of the Flask container handling the request.
    - **flask_port**: Internal port of the Flask container.
    - **request_type**: Type of request (GET or POST).
    - **created_at**: Timestamp of when the record was created.

- **Persistence**:
  - Uses a Docker volume (`db-data`) to ensure data persistence across container restarts.

---

## Deployment

### Docker Compose File

The `docker-compose.yml` file orchestrates the deployment of all services (NGINX, Flask, PostgreSQL). It defines:

- **Flask App**:
  - Scaled to 3 replicas (`deploy.replicas: 3`).
  - Exposes port 5000 internally to the app network.

- **NGINX**:
  - Routes all traffic to Flask containers on the app network.
  - Accessible on port 80 on the host.

- **PostgreSQL**:
  - Stores receipt data persistently using a Docker volume.

---

### Commands

1. **Start Services**:
   ```bash
   docker-compose up --build --scale flask-app=3 -d
2. **Stop Services**:
    ```bash
    docker-compose down
3. **Check Logs**:
    ```bash
    docker-compose logs -f

### Request Flow
  - A client sends a request to [http://localhost](http://localhost) (handled by NGINX).
  - NGINX forwards the request to one of the Flask replicas based on the load-balancing policy.
  - The Flask app processes the request and interacts with the PostgreSQL database.
  - NGINX adds debugging headers (e.g., `X-Backend-Server`) to responses for tracing.

---

## Key Features

### Load Balancing

  - NGINX ensures that traffic is distributed among Flask replicas.
  - This improves scalability and fault tolerance by balancing the load across multiple Flask containers.

### Health Checks
  
  Both NGINX and Docker Compose perform health checks to ensure:
  
  - NGINX is operational.
  - Flask containers are responding.
  - PostgreSQL database is available.
  - Unhealthy services are not included in the request routing.

### Data Persistence
  - PostgreSQL data is stored in a persistent volume (`db-data`).
  - This ensures no data is lost during container restarts or recreations.

### Request Metadata Logging
  
  Every request (`POST` or `GET`) is logged with the following metadata:
  
  - Flask container name
  - Flask container port
  - Request type (`GET` or `POST`)
  - Timestamp of the request
  
  This helps with debugging and monitoring.

---

## Testing
  
### **Check NGINX Health**
  To test if the NGINX load balancer is operational, use:

  ```bash
  curl http://localhost/health

### **Process a Receipt**

  To process a receipt, send a `POST` request to the `/receipts/process` endpoint:

  ```bash
  curl -X POST http://localhost/receipts/process \
  -H "Content-Type: application/json" \
  -d '{
      "retailer": "Target",
      "purchaseDate": "2023-01-01",
      "purchaseTime": "15:30",
      "total": "20.00",
      "items": [
          { "shortDescription": "Mountain Dew", "price": "10.00" },
          { "shortDescription": "Doritos", "price": "10.00" }
      ]
  }'


---


### Get Points for a Receipt

  - To retrieve the points for a processed receipt, send a GET request to the /receipts/<receipt_id>/points endpoint. Replace <receipt_id> with the actual receipt ID.

  ```bash
  curl -X GET http://localhost/receipts/<receipt_id>/points

---

### Notes

- Ensure all services are running before testing (docker-compose up).
- Use docker-compose logs -f to monitor the system in real-time.
- Requests should only be routed through NGINX, and Flask replicas should remain unreachable directly.