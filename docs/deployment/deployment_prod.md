# Production Deployment

Production environment uses a docker container (`Dockerfile.prod`) that uses Gunicorn as the WWSGI server with multiple workers.

### Important Information

- **Container User**: Runs as `fedadmin` user (UID/GID: 5000) for security
- **Task Queue**: Uses SQLAlchemyJobStore for persistent and deduplicated task scheduling across multiple workers
- **Volume Mapping**: Bind mounts for specific directories
  - Storage path: `./data/storage/` (host) ↔ `/app/app/storage/` (container)
  - Database path: `./data/instance/fedadmin-prod.db` (host) ↔ `/app/instance/fedadmin-prod.db` (container)
  - Log path: `./data/logs/` (host) ↔ `/var/log/fedadmin/` (container)
- **Scheduler Table**: Task queue stored in existing database as `scheduler_jobs` table
- **Backup**: Regularly backup `./data/instance/`, `./data/storage/`, and `./data/logs/` directories on host server

### Steps

1. **Prepare the host system** (Linux only)
   
   > **⚠️ Important:** Check if UID 5000 is already in use to avoid permission issues.
   >
   > **Check if UID 5000 is available:**
   > ```bash
   > # Check if UID 5000 is already in use
   > getent passwd 5000
   > ```
   >
   > **💡 Note:** If UID 5000 conflicts, change it in:
   > - `Dockerfile.prod` (line 16): `groupadd -g 5000` and `useradd -u 5000`

   ```bash
   # Create fedadmin group and user (if not already exists)
   sudo groupadd -g 5000 fedadmin
   sudo useradd -u 5000 -g fedadmin -m -s /bin/bash fedadmin
   
   # Create data directories and set ownership
   sudo mkdir -p data/instance data/storage data/logs
   sudo chown -R fedadmin:fedadmin data/instance data/storage data/logs
   sudo chmod 750 data/instance data/storage data/logs
   ```

   **💡 Tip:** We don't suggest, and never tested hosting the container on platforms other than a linux server for production.

2. **Prepare configuration file**
   
   ```bash
   # Create .env file from template
   cp .env.prod.example .env
   ```

   > **⚠️ Important:** 
   > - You must change all REQUIRED values before building the docker image! 
   > - Always generate secure random keys using `openssl rand -hex 32`.
   > - The application requires email configuration for password recovery functionality. Without proper email configuration, the password recovery feature will not work.
   > - Any changes in this configuration file needs a container restart.

3. **Build and start the application**
   
   ```bash
   # Build production image
   docker build -f Dockerfile.prod -t fedadmin:prod .
   
   # Start with Docker Compose
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Initialize database and certificates**
    
    After the container is ready, run:

    ```bash
    # Generate signing certificates for SAML metadata
    docker-compose -f docker-compose.prod.yml exec web flask init-certs

    # Create/update database tables using flask-migration
    docker-compose -f docker-compose.prod.yml exec web flask db upgrade

    # Insert default data if tables are empty:
    # - Default roles (federation, full_member, sp_member)
    # - Federation configuration
    # - Federation Admin Org organization
    # - fedadmin user with randomly generated password (fed@example.com)
    docker-compose -f docker-compose.prod.yml exec web flask init-db
    ```

5. **Verify the application**
   
   ```bash
   curl https://your-domain.com
   ```

### What Each Command Does

| Command | Description |
|---------|-------------|
| `flask db upgrade` | Creates or updates database tables based on the migration scripts. This command creates the schema using flask-migration. |
| `flask init-certs` | Generates X.509 certificate and private key for signing federation metadata. |
| `flask init-db` | Inserts default data if tables are empty: default roles (federation, full_member, sp_member), federation configuration, federation admin organization, and admin user (fed@example.com). This command does not modify existing data. **Note:** The generated password is only displayed once during initialization. |

### Daily Operations

- **View application logs**:
  1.  Using Docker logs: `docker-compose -f docker-compose.prod.yml logs -f web`. This shows the Gunicorn and Flask application's stdout/stderr output.
  2.  Using log file: Application logs are also written to `/var/log/fedadmin/app.log` inside the container. `docker-compose -f docker-compose.prod.yml exec web tail -f /var/log/fedadmin/app.log`
- **Monitor container status**: `docker-compose -f docker-compose.prod.yml ps`
- **Stop all containers**: `docker-compose -f docker-compose.prod.yml down`
- **Restart container**: `docker-compose -f docker-compose.prod.yml restart web`
- **Execute Flask commands inside container**:
  
  > **⚠ Important:** In production, avoid executing commands that directly modify the database or production files. Use the web interface for all business operations. The `flask init-db` and `flask init-certs` commands are only intended for initial setup as described in Step 4.

  ```bash
  # List all available Flask commands
  docker-compose -f docker-compose.prod.yml exec web flask --list-commands
  ```

### Troubleshooting

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

2. **Common issues and solutions**
   
   | Error | Solution |
   |-------|----------|
   | `Port already in use` | Stop other services using port 5000, or change port in `docker-compose.prod.yml` |
   | `Permission denied` | Check file permissions, ensure running as correct user |

3. **Reset and start over**
   ```bash
   # Stop and remove all containers and volumes
   docker-compose -f docker-compose.prod.yml down -v
   
   # Rebuild and restart
   docker-compose -f docker-compose.prod.yml up -d --build
   ```

### Production Considerations

1. **Security Configuration**
   - Use strong random keys (at least 32 characters)
   - Production environment automatically validates required environment variables on startup
   - Missing required variables will cause startup failure

2. **Recommend using reverse proxy**
   - HTTPS Certificate Management: Using a reverse proxy (such as Nginx or Apache) makes it convenient to manage SSL certificates
   - Public Path Mapping: The `/path/to/your/project/app/storage/public/` directory needs to be mapped as a public path to allow access to federation metadata files


## Scheduled Tasks

TODO

For detailed information about the system's scheduled tasks, including configuration details and processes, please refer to the [Scheduled Tasks Guide](scheduled_tasks.md). This document provides comprehensive documentation on:

- Regenerate Metadata Job
- Check eduGAIN Updates Job