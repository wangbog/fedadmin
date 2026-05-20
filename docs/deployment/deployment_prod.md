# Production Deployment

Production environment uses a docker container (`Dockerfile.prod`) that uses Gunicorn as the WWSGI server with multiple workers.

## Important Information

- **Container User**: Runs as `fedadmin` user (UID/GID: 5000) for security
- **Volume Mapping**: Bind mounts for specific directories
  - Storage path: `./data/storage/` (host) ↔ `/app/app/storage/` (container)
  - Database path: `./data/instance/fedadmin-prod.db` (host) ↔ `/app/instance/fedadmin-prod.db` (container)
  - Log path: `./data/logs/` (host) ↔ `/var/log/fedadmin/` (container)
- **Backup**: Please regularly backup above directories on host server

## Setup Steps

1. **Prepare the host system** (Linux only)

   **💡 Note:** We don't suggest, and never tested hosting the container on platforms other than a linux server for production.

   **⚠️ Important:** The docker container is running as `fedadmin` user with UID 5000, check if UID 5000 is already in use on host server to avoid confliction.

   ```bash
   getent passwd 5000
   ```

   If UID 5000 is already in use, change our docker file to use another UID:
   - `Dockerfile.prod`: `groupadd -g 5000` and `useradd -u 5000`

   Create `fedadmin` group and user (if you're using UID other than 5000, change it accordingly)

   ```bash
   sudo groupadd -g 5000 fedadmin
   sudo useradd -u 5000 -g fedadmin -m -s /bin/bash fedadmin
   ```

   Add user `fedadmin` to `docker` group, so it can build and run docker images

   ```bash
   sudo usermod -aG docker fedadmin
   ```

   Create the work dir, copy or clone project files

   ```bash
   sudo mkdir -p /data/fedadmin

   # copy your project files to /data/fedadmin, or git clone it in /data/fedadmin
   ...

   sudo chown -R fedadmin:fedadmin /data
   ```

   Switch to user `fedadmin`, following steps are all under `fedadmin` user

   ```bash
   su www
   cd /data/fedadmin
   ```

   Create bind mount directories and set ownership

   ```bash
   mkdir -p data/instance data/storage data/logs
   sudo chmod 750 -R data
   ```

2. **Prepare configuration file**

   ```bash
   # Create .env.prod file from template
   cp .env.prod.example .env
   ```

   **⚠️ Important:** 
   - You must change all REQUIRED values before building the docker image! 
   - Always generate secure random keys using `openssl rand -hex 32`.
   - The application requires email configuration for password recovery functionality. Without proper email configuration, the password recovery feature will not work.
   - Any changes in this configuration file needs a container restart.

3. **Build and start the application**

   ```bash
   # Build production image
   docker compose -f docker-compose.prod.yml build

   # Start with Docker Compose
   docker compose -f docker-compose.prod.yml up -d
   ```

4. **Initialize federation metadata certificates and database**

   After the container is ready, run:

   ```bash
   # Generate signing certificates for SAML metadata
   docker exec fedadmin flask init-certs

   # Create/update database tables using flask-migration
   docker exec fedadmin flask db upgrade

   # Insert default data if tables are empty:
   # - Default roles (federation, full_member, sp_member)
   # - Federation configuration
   # - Federation Admin Org organization
   # - fedadmin user with randomly generated password (fed@example.com)
   docker exec fedadmin flask init-db
   ```

   **⚠️ Important:** The generated password will be shown on console, please keep it safe!

   Check the files are generate:

   ```bash
   # Enter the docker 
   docker exec -it fedadmin /bin/bash
   
   # Check the generated files
   fedadmin@<container_id>:/app$ ls app/storage/private/federation/
   fed.crt  fed.key

   fedadmin@<container_id>:/app$ ls instance/
   fedadmin-prod.db
   ```

## Access the application

After completing the setup steps, verify everything is working:

1. Visit http://hostip:5000/
2. Try logging in with the federation admin account: `fed@example.com` / `the generated password`

## Daily Operations

- **View application logs**:
  1.  Using Docker logs: On your host machine, run `docker-compose -f docker-compose.prod.yml logs -f web`. This shows the Gunicorn and Flask application's stdout/stderr output.
  2.  Using log file: Application logs are also written to `/var/log/fedadmin/app.log` inside the container. You can view it inside the container with `docker exec fedadmin sh -c "tail -f /var/log/fedadmin/app.log"`, or directly on the host at `./data/logs/app.log`.
- **Monitor container status**: `docker ps -a | grep fedadmin`
- **Stop all containers**: `docker stop fedadmin`
- **Restart container**: `docker restart fedadmin`

## Troubleshooting

If the container fails to start, follow these steps:

1. **View container logs**

   ```bash
   # Find container ID
   docker ps -a | grep fedadmin

   # View logs (replace <container-id> with actual ID)
   docker logs <container-id>

   # Or follow logs in real-time
   docker logs -f <container-id>
   ```

2. **Reset and start over**
   ```bash
   # Stop and remove all containers and data volumes
   docker stop fedadmin && docker rm fedadmin

   # Rebuild and start the container
   docker compose -f docker-compose.prod.yml up -d --build
   ```

### Production Considerations

1. **Security Configuration**
   - Use strong random keys (at least 32 characters)
   - Production environment automatically validates required environment variables on startup
   - Missing required variables will cause startup failure

2. **Use a reverse proxy (such as Nginx or Apache)**
   - HTTPS Certificate Management.
   - Security Settings.
   - Public Path Mapping: The container directory `/app/app/storage/public/` is mapped to the host path `./data/storage/public/`. This directory contains federation related public metadata files (e.g., `fed-metadata.xml`, `fed-metadata-edugain.xml`, `fed-metadata-beta.xml` under `./data/storage/public/federation/`). A reverse proxy is recommended to expose these metadata files publicly.

## Scheduled Tasks

TODO

- Regenerate Metadata Job
- Check eduGAIN Updates Job