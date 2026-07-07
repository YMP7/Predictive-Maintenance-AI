# Run and Deployment Guide
## AI-Powered Digital Twin & Predictive Maintenance System

This guide provides step-by-step instructions on how to run the Predictive Maintenance Digital Twin system locally and deploy it securely to the internet.

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
     cp .env.example .env # Create .env from the template and configure variables
     ```

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
   - Return to the root directory:
     ```bash
     cd ..
     ```

4. **Launch the Unified Integrated Server**:
   - The integrated server hosts both the React build (SPA) and the REST API on a single port:
     ```bash
     python integrated_server.py
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
- Clone your repository to the `/opt/ai-digital-twin` folder and create your `.env` file. Ensure `API_KEY` is configured to secure POST control endpoints.

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
      --set-env-vars="API_KEY=your_secure_key,LOG_LEVEL=INFO"
  ```
- Cloud Run will automatically generate an HTTPS URL (e.g. `https://ai-digital-twin-xyz.a.run.app`) for internet access.

---

### 3. Production Hardening Checklist

Before exposing the application to the internet, verify that the following security policies are in place:

1. **API Key Authentication**: 
   - Set a secure token in the `API_KEY` environment variable. This will force API key header validation (`X-API-Key`) on all post endpoints like `/api/simulation/start`, `/api/simulation/stop`, and `/api/machines/{machine_id}/fault`, preventing unauthorized controls.
2. **Disable Simulation (Optional)**:
   - In production, set `SIMULATION_ENABLED=false` to stop simulated sensor generation, and hook up physical sensors to the `DataService` telemetry pipeline instead.
3. **Secure Secrets**:
   - Never commit your `.env` file containing SMTP passwords or Twilio SID tokens to Git. Use environment secrets managers in AWS, GCP, or GitHub Actions.
4. **CORS Configuration**:
   - Set `CORS_ORIGINS` to your domain URL (e.g. `https://yourdomain.com`) instead of the wildcard `*` to restrict dashboard queries to authorized domains only.
