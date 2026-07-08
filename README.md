# Run and Deployment Guide
## AI-Powered Digital Twin & Predictive Maintenance System

This guide provides step-by-step instructions on how to run the Predictive Maintenance Digital Twin system locally and deploy it securely to the internet.

### Project Structure
- `client/` - React SPA Frontend
- `server/` - Python FastAPI Backend
- `docs/` - Project documentation
- `scripts/` - Verification and utility scripts

---

### 1. How to Run Locally

There are two primary methods to run the unified application (FastAPI backend + React frontend) on your local machine.

#### Option A: Direct Python and Node.js Execution (Recommended for Development)

##### Prerequisites:
- Python 3.8 or later
- Node.js 18 or later
- npm or pnpm package manager

##### Steps:
1. **Clone/Navigate to the Repository**:
   ```bash
   cd /path/to/AI-Powered-Digital-Twin-Predictive-Maintenance
   ```

2. **Set up the Backend**:
   - Create and activate a Python virtual environment:
     ```bash
     python -m venv venv
     # On Windows:
     .\venv\Scripts\activate
     # On macOS/Linux:
     source venv/bin/activate
     ```
   - Install the Python dependencies:
     ```bash
     pip install -r requirements.txt
     ```
    - Initialize environment variables:
      ```bash
      cp .env.example .env # Create .env from the template
      ```
    - **Important:** Edit `.env` and generate a secure `JWT_SECRET_KEY`:
      ```bash
      openssl rand -hex 32
      ```
      The backend will fail to start if this is not set.

3. **Build the Frontend Client**:
   - Navigate to the client directory and install npm packages:
     ```bash
     cd client
     npm install
     ```
   - Build the production assets of the React single-page app:
     ```bash
     npm run build
     ```
4. **Mosquitto MQTT Broker (Optional for IoT Ingestion)**:
   - If you want to use the MQTT ingestion feature, start the Mosquitto broker using Docker:
     ```bash
     docker-compose up -d mosquitto-init mosquitto
     ```
   - This sets up Eclipse Mosquitto on port `1883` with password authentication.

5. **TimescaleDB (Required for Data Persistence)**:
   - Start the TimescaleDB container:
     ```bash
     # Set the password (use a strong password in production)
     export TSDB_PASSWORD=your_secure_password
     docker-compose up -d timescaledb
     ```
   - Run the schema migration:
     ```bash
     python scripts/migrate.py
     ```
   - Seed development accounts (dev/CI only — **never run in production**):
     ```bash
     python scripts/seed_dev.py
     ```
   - Add `DATABASE_URL` to your `.env`:
     ```
     DATABASE_URL=postgresql://dtwin:your_secure_password@localhost:5432/digital_twin
     ```
   - Return to the root directory:
     ```bash
     cd ..
     ```

4. **Launch the Unified Integrated Server**:
   - The integrated server hosts both the React build (SPA) and the REST API on a single port:
     ```bash
     python server/integrated_server.py
     ```
   - Open your web browser and navigate to `http://localhost:8000`.

---

#### Option B: Docker Compose Execution (Recommended for Testing & Production)

##### Prerequisites:
- Docker and Docker Compose installed on your host machine.

##### Steps:
1. **Navigate to the Project Root**:
   ```bash
   cd /path/to/AI-Powered-Digital-Twin-Predictive-Maintenance
   ```

2. **Configure Environment Variables**:
   - Ensure you have a `.env` file present in the root directory.

3. **Build and Run the Containers**:
   ```bash
   docker-compose up --build -d
   ```

4. **Verify Deployment**:
   - Check the container status:
     ```bash
     docker-compose ps
     ```
   - Ensure the health status transitions to `healthy`.
   - Access the dashboard at `http://localhost:8000`.
   - To stop the services:
     ```bash
     docker-compose down
     ```

---

### 2. How to Deploy to the Internet

For production internet deployment, you must move from local/ephemeral configurations to persistent, secure cloud environments. 

#### Option A: Deployment on a Cloud Virtual Machine (AWS EC2, DigitalOcean, GCP)

This is the standard approach using a virtual machine running Linux (e.g. Ubuntu 20.04/22.04 LTS).

##### 1. Provision VM and Install Docker:
- SSH into your cloud server and install Docker & Docker Compose:
  ```bash
  sudo apt-get update
  sudo apt-get install -y docker.io docker-compose
  ```

##### 2. Deploy Project Files:
- Clone your repository to the `/opt/ai-digital-twin` folder and create your `.env` file. Ensure `JWT_SECRET_KEY` is configured to secure the authentication system.

##### 3. Run the Container Stack:
- Start the server on localhost inside the Docker network:
  ```bash
  docker-compose up -d
  ```

##### 4. Set up Nginx as a Reverse Proxy & SSL (HTTPS):
- Install Nginx:
  ```bash
  sudo apt-get install -y nginx
  ```
- Configure Nginx to forward public traffic on ports 80 and 443 to the internal port 8000. Create `/etc/nginx/sites-available/digitaltwin` with the following configuration:
  ```nginx
  server {
      listen 80;
      server_name yourdomain.com;

      location / {
          proxy_pass http://127.0.0.1:8000;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
      }
  }
  ```
- Enable the configuration and restart Nginx:
  ```bash
  sudo ln -s /etc/nginx/sites-available/digitaltwin /etc/nginx/sites-enabled/
  sudo nginx -t
  sudo systemctl restart nginx
  ```
- Secure with Let's Encrypt SSL/TLS certificates:
  ```bash
  sudo apt-get install -y certbot python3-certbot-nginx
  sudo certbot --nginx -d yourdomain.com
  ```

---

#### Option B: Deploying on Container Platforms (Google Cloud Run, AWS ECS)

Container platforms provide serverless scaling, automatic SSL termination, and high availability.

##### 1. Switch Database from SQLite to Cloud PostgreSQL:
SQLite is a local file-based database. Container platforms use ephemeral file systems, meaning your database will be wiped on restarts.
- Modify `data_service.py` or enable environment overrides to connect to a persistent managed cloud database (e.g., AWS RDS PostgreSQL or Neon DB).
- Set `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD` in your container environment variables.

##### 2. Build and Push the Docker Image:
- Build your image locally or via cloud build systems:
  ```bash
  docker build -t gcr.io/your-project-id/ai-digital-twin:latest .
  ```
- Push it to the container registry:
  ```bash
  docker push gcr.io/your-project-id/ai-digital-twin:latest
  ```

##### 3. Deploy the Container (e.g. Google Cloud Run):
- Deploy the container and expose port 8000:
  ```bash
  gcloud run deploy ai-digital-twin \
      --image gcr.io/your-project-id/ai-digital-twin:latest \
      --platform managed \
      --port 8000 \
      --allow-unauthenticated \
      --set-env-vars="JWT_SECRET_KEY=your_secure_generated_key,LOG_LEVEL=INFO"
  ```
- Cloud Run will automatically generate an HTTPS URL (e.g. `https://ai-digital-twin-xyz.a.run.app`) for internet access.

---

### 3. Production Hardening Checklist

Before exposing the application to the internet, verify that the following security policies are in place:

1. **JWT Secret Key**: 
   - A secure, 32-byte hexadecimal string MUST be set in the `JWT_SECRET_KEY` environment variable (`openssl rand -hex 32`). This is used to sign authentication tokens. The app will refuse to start in production without it.
2. **Role-Based Access Control (RBAC)**:
   - Control endpoints (like `/api/machines/{machine_id}/fault` and `/api/simulation/start`) are protected and require an authentication token from an account with the `admin` role. Ensure production passwords for admin accounts are strong and securely stored.
3. **Disable Simulation (Optional)**:
   - In production, set `SIMULATION_ENABLED=false` to stop simulated sensor generation, and hook up physical sensors to the `DataService` telemetry pipeline instead.
4. **Secure Secrets**:
   - Never commit your `.env` file containing passwords or JWT secrets to Git. Use environment secrets managers in AWS, GCP, or GitHub Actions.
5. **CORS Configuration**:
   - Set `CORS_ORIGINS` to your domain URL (e.g., `https://yourdomain.com`) to restrict dashboard queries to authorized domains only. It defaults to local dev URLs if unset.
