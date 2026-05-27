# Production Deployment

The production environment uses Docker Compose `docker-compose.prod.yml` with the production `Dockerfile.prod`.

The container includes the Linux system packages and Python dependencies required by FedAdmin, and runs Gunicorn as the WSGI production server.

## Important Information

- **Container User**: Runs as `fedadmin` user (UID/GID: 5000)
- **Volume Mapping**: Bind mounts for specific directories
  - Storage path: `./data/storage/` (host) ↔ `/app/app/storage/` (container)
  - Database path: `./data/instance/fedadmin-prod.db` (host) ↔ `/app/instance/fedadmin-prod.db` (container)
  - Log path: `./data/logs/` (host) ↔ `/var/log/fedadmin/` (container)
- **Directory Permission**: The `./data` directories use mode `750` for security and are owned by `fedadmin:fedadmin`.
- **Backup**: Regularly back up the following directories/files on the host server:
  - `./data/instance/` (SQLite database)
  - `./data/storage/` (metadata, certificates, uploaded files)
  - `./data/logs/` (application logs)
  - `.env` (environment configuration)

## Setup Steps

1. **Prepare the host system**

   **💡 Note:** We do not recommend or have tested hosting the container on platforms other than a Linux server for production.

   **⚠️ Important:** The docker container runs as the `fedadmin` user with UID 5000. Create a fedadmin user with UID 5000 on the host system.

   Check if UID 5000 is already in use on the host server to avoid conflict:

   ```bash
   getent passwd 5000
   ```

   If UID 5000 is already in use, change the Dockerfile.prod to use another UID:
   - `Dockerfile.prod`: `groupadd -g 5000` and `useradd -u 5000`

   Create `fedadmin` group and user (if you're using UID other than 5000, change it accordingly):

   ```bash
   sudo groupadd -g 5000 fedadmin
   sudo useradd -u 5000 -g fedadmin -m -s /bin/bash fedadmin
   ```

   Add user `fedadmin` to `docker` group, so it can build and run docker images:

   ```bash
   sudo usermod -aG docker fedadmin
   ```

   Create the work dir, copy or clone project files:

   ```bash
   sudo mkdir -p /data/fedadmin

   # copy your project files to /data/fedadmin, or git clone it in /data/fedadmin
   ...

   sudo chown -R fedadmin:fedadmin /data/fedadmin
   ```

   Switch to user `fedadmin`, following steps are all under the `fedadmin` user:

   ```bash
   sudo -u fedadmin bash
   cd /data/fedadmin
   ```

   Create bind mount directories and set secure permissions:

   ```bash
   mkdir -p data/instance data/storage data/logs
   # Restrict data directories to fedadmin owner/group
   chmod 750 -R data
   ```

2. **Configure Nginx Reverse Proxy**

   For production deployment, it is **highly recommended** to deploy an Nginx reverse proxy with HTTPS in front of the Gunicorn service. It provides TLS termination, request buffering, security hardening and standard production deployment architecture.

   If you enable Nginx HTTPS reverse proxy, you **must** add the `X-Forwarded-Proto` header. This passes the real HTTPS scheme to Flask/Gunicorn. 

   Example Nginx locations:

   ```nginx
   location / {
       proxy_pass http://127.0.0.1:5000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
   }
   ```

   This matches the built-in Gunicorn production configuration:

   ```python
   secure_scheme_headers = {"X-Forwarded-Proto": "https"}
   forwarded_allow_ips = "*"
   ```

   The production configuration enables `SESSION_COOKIE_SECURE = True` by default (see `config.py ProductionConfig`), which restricts session cookies to HTTPS-only connections for security.

   Please follow the rules below according to your actual deployment method:

   - **With Nginx HTTPS reverse proxy (Production Standard)**
     Keep default `SESSION_COOKIE_SECURE = True`.
     Ensure the above `X-Forwarded-Proto` header is configured in Nginx, otherwise Flask cannot identify HTTPS connections correctly, resulting in login failure and 'The CSRF tokens do not match' errors.

   - **Without Nginx Proxy (Direct HTTP access for temporary testing)**
     You **must** manually set `SESSION_COOKIE_SECURE = False` in `config.py` before starting the container.
     Browsers will refuse to carry secure cookies over plain HTTP, which will cause login failure and CSRF token invalidation.
     This disables the HTTPS-only requirement for session cookies, allowing login and CSRF validation to work correctly over HTTP.

   **Public metadata files:**
   The container directory `/app/app/storage/public/` is mapped to the host path `./data/storage/public/`. This directory contains federation related public metadata files (e.g., `fed-metadata.xml`, `fed-metadata-edugain.xml`, `fed-metadata-beta.xml` under `./data/storage/public/federation/`). A reverse proxy is recommended to expose these metadata files publicly.

   Example Nginx locations:

   ```nginx
   location ^~ /public/ {
       alias /data/fedadmin/data/storage/public/;
       add_header Cache-Control "public, max-age=300";
   }
   ```

   In this example, `/data/fedadmin` is the project root on the host. Replace `/data/fedadmin/data/storage/public/` with the absolute path of your deployment's `./data/storage/public/` directory. The `/public/` URL prefix is used to avoid conflicts with FedAdmin's application routes such as `/federation/...`.

   Because the host `data` directory is created with restricted permissions, ensure the Nginx worker user can traverse the public storage path. For example, if Nginx runs as the `nginx` user:

   ```bash
   sudo usermod -aG fedadmin nginx
   sudo systemctl restart nginx
   ```

   Example public metadata URLs:

   ```text
   https://<host>/public/federation/fed-metadata.xml
   https://<host>/public/federation/fed-metadata-edugain.xml
   https://<host>/public/federation/fed-metadata-beta.xml
   ```

3. **Prepare the configuration file**

   ```bash
   # Create .env.prod file from template
   cp .env.prod.example .env

   # Protect sensitive environment variables
   chmod 600 .env
   ```

   **⚠️ Important:** 
   - You must change all REQUIRED values before building the docker image! 
   - Always generate secure random keys using `openssl rand -hex 32`.
   - The application requires email configuration for password recovery functionality. Without proper email configuration, the password recovery feature will not work.
   - Keep `.env` readable only by the deployment user because it contains sensitive secrets.
   - Any changes in this configuration file needs a container restart.

4. **Build and start the production container**

   **⚠️ Important:** The default timezone is `TZ=Asia/Shanghai` for China. Modify it in `docker-compose.prod.yml` if your server is located in another region, so the application logs use the correct local time.

   Run from the project root:

   ```bash
   docker compose -f docker-compose.prod.yml up --build -d
   ```

   The first build may take a few minutes. After the container starts, Flask runs automatically inside the `web` service.

5. **Initialize federation metadata certificates and database**

   After the container is up, run these commands from the project root. The execution order cannot be changed: generate certificates, upgrade the database, then insert initial data.

   ```bash
   # Generate signing certificates for SAML metadata
   docker compose -f docker-compose.prod.yml exec --user fedadmin web flask init-certs

   # Create/update database tables using Flask-Migrate
   docker compose -f docker-compose.prod.yml exec --user fedadmin web flask db upgrade

   # Insert default data if tables are empty:
   # - Default roles (federation, full_member, sp_member)
   # - Federation configuration
   # - Federation Admin Org organization
   # - fedadmin user with randomly generated password (fed@example.com)
   docker compose -f docker-compose.prod.yml exec --user fedadmin web flask init-db
   ```

   **⚠️ Important:** The generated password will be shown on console, please keep it safe!

   Check the generated files:

   ```bash
   docker compose -f docker-compose.prod.yml exec --user fedadmin web ls app/storage/private/federation/
   docker compose -f docker-compose.prod.yml exec --user fedadmin web ls instance/
   ```

   Expected files include:

   ```text
   app/storage/private/federation/fed.crt
   app/storage/private/federation/fed.key
   instance/fedadmin-prod.db
   ```

## Access the Application

1. Visit `http://<host_ip>:5000/` (without nginx) or `https://<host>/` (with nginx).
2. Log in with `fed@example.com` and the password generated by `flask init-db`.

## Scheduled Tasks

See [Scheduled Tasks](scheduled_tasks.md) for details.

Configure crontab as the `fedadmin` user on the host server to run these commands automatically:

   ```bash
   sudo -u fedadmin mkdir -p /data/fedadmin/data/host_logs

   # Edit crontab
   sudo -u fedadmin crontab -e

   # Add crontab rules.
   # -T disables pseudo-terminal allocation for non-interactive cron execution.
   30 2 * * * cd /data/fedadmin && docker compose -f docker-compose.prod.yml exec -T --user fedadmin web flask regenerate-metadata >> /data/fedadmin/data/host_logs/cron.log 2>&1
   15 * * * * cd /data/fedadmin && docker compose -f docker-compose.prod.yml exec -T --user fedadmin web flask check-edugain-updates >> /data/fedadmin/data/host_logs/cron.log 2>&1
   ```

**Note:** Adjust the time and log path according to your deployment configuration. If `docker compose` is not available in cron's PATH, use the absolute path to your Docker CLI. Configure logrotate for `/data/fedadmin/data/host_logs/cron.log` to prevent long-term log file growth.

Check the cron log file to verify task execution:

   ```bash
   # View cron log on host server
   cat ./data/host_logs/cron.log
   ```

The cron log only contains cron command output. Application logs produced by these commands are written to the configured application log file:

   ```bash
   tail -f ./data/logs/app.log
   ```

## Daily Operations

- **Open a shell inside the container**:

  ```bash
  docker compose -f docker-compose.prod.yml exec --user fedadmin web bash
  ```

- **Change environment variables**:

  ```bash
  # After editing .env
  docker compose -f docker-compose.prod.yml restart web
  ```

- **View logs**:

  ```bash
  # Container stdout/stderr logs
  docker compose -f docker-compose.prod.yml logs -f web

  # Application file logs
  tail -f ./data/logs/app.log
  ```

  `docker compose logs` shows the container stdout/stderr stream. Application logs are written to `/var/log/fedadmin/app.log` inside the container, which is mounted to `./data/logs/app.log` on the host.

- **Stop the container**:

  ```bash
  docker compose down
  ```

## Troubleshooting

1. **View container status and logs**

   ```bash
   docker compose -f docker-compose.prod.yml ps
   docker compose -f docker-compose.prod.yml logs -f web
   ```

2. **Rebuild and restart**

   ```bash
   docker compose -f docker-compose.prod.yml down
   docker compose -f docker-compose.prod.yml up --build -d
   ```

3. **Run Flask commands manually inside the container**

   ```bash
   docker compose -f docker-compose.prod.yml exec --user fedadmin web bash
   flask --help
   ```

### Production Considerations

1. **Security Configuration**
   - Use strong random keys (at least 32 characters)
   - Production environment automatically validates required environment variables on startup
   - Missing required variables will cause startup failure

2. **Use a reverse proxy (such as Nginx or Apache)**
   - HTTPS Certificate Management.
   - Security Settings.
   - Public Path Mapping: Expose `./data/storage/public/` through a public URL prefix such as `/public/` for federation metadata publication.

3. **File Permission and Owner**
   - Project files and mounted data directories should be owned by `fedadmin:fedadmin`.
   - Sensitive files such as `.env` and `./data/storage/private/federation/fed.key` should use permission `600`.

4. **Network and Firewall**
   - Open port `443` for HTTPS web access and metadata publication.
   - If using Nginx as the production entry point, restrict direct Gunicorn access on port `5000` to localhost or a trusted internal network.

5. **Metadata Availability**
   - Ensure the `/public/` URL path remains accessible so federation metadata can be fetched by IdPs, SPs, eduGAIN, or other federation services.

