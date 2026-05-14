# Production Deployment

Production environment uses a separate Dockerfile (`Dockerfile.prod`) that excludes development tools and uses Gunicorn as the WSGI server.

### Important Information

- **Container User**: Runs as `fedadmin` user (UID/GID: 5000) for security
- **Volume Mapping**: Bind mounts for specific directories
  - Storage path: `./storage/` (host) ↔ `/app/storage/` (container)
  - Database path: `./instance/fedadmin-prod.db` (host) ↔ `/app/instance/fedadmin-prod.db` (container)
  - Log path: `./logs/` (host) ↔ `/var/log/fedadmin/` (container)
- **Backup**: Regularly backup `./instance/` and `./storage/` directories to a secure off-site location

### Steps

1. **Prepare the host system** (Linux/macOS only)
   
   > **⚠️ Important:** Check if UID 5000 is already in use to avoid permission issues.
   >
   > **Check if UID 5000 is available:**
   > ```bash
   > # Check if UID 5000 is already in use
   > getent passwd 5000
   > 
   > # If it returns a user, choose a different UID (e.g., 5001, 6000, etc.)
   > ```
   >
   > **💡 Note:** If UID 5000 conflicts, change it in:
   > - `Dockerfile.prod` (line 16): `groupadd -g 5000` and `useradd -u 5000`
   > - This README (update all UID/GID references)
   >
   > **💡 Tip:** Windows users do not need to perform this step as Docker Desktop handles permissions automatically.
   
   ```bash
   # Create fedadmin group and user (if not already exists)
   sudo groupadd -g 5000 fedadmin
   sudo useradd -u 5000 -g fedadmin -m -s /bin/bash fedadmin
   
   # Create data directories and set ownership
   sudo mkdir -p instance storage
   sudo chown -R fedadmin:fedadmin instance storage
   sudo chmod 750 instance storage
   ```

2. **Prepare configuration file**
   
   ```bash
   # Create .env file from template
   cp .env.prod.example .env
   
   # Edit .env and replace placeholder values with your actual configuration
   ```

   > **⚠️ Important:** You must change all values before deploying to production! Never use the example values from `.env.prod.example` in production. Always generate secure random keys using `openssl rand -hex 32`.
   >
   > **⚠️ Important:** The application requires email configuration for password recovery functionality. Before deploying, you must configure the mail server settings in your `.env` file. Without proper email configuration, the password recovery feature will not work.

3. **Build and start the application**
   
   ```bash
   # Build production image
   docker build -f Dockerfile.prod -t fedadmin:prod .
   
   # Start with Docker Compose
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Initialize certificates and database**
   
   > **⚠ Important:** These commands will prompt for confirmation if files already exist. Regenerating certificates will invalidate any previously distributed public certificates! Initializing the database will delete all existing data!
   
   ```bash
   # Generate signing certificates for SAML metadata
   docker-compose -f docker-compose.prod.yml exec web flask init-certs

   # Initialize database, create default federation configuration, and automatically create:
   # - Federation Admin Org organization
   # - fedadmin user (fed@example.com / fedadmin)
   docker-compose -f docker-compose.prod.yml exec web flask init-db
   ```

5. **Create admin organization and user**
   
   > **⚠ Important:** The `init-db` command automatically creates the required federation admin organization and user. Skip these commands unless you need additional organizations or users.
   
   ```bash
   # Optional: Create additional organizations
   docker-compose -f docker-compose.prod.yml exec web flask createorganization \
     --name="Additional Organization" \
     --description="An additional organization" \
     --type=full_member \
     --url="https://your-domain.org"
   
   # Optional: Create additional users
   docker-compose -f docker-compose.prod.yml exec web flask createuser \
     --username=additional_admin \
     --email=additional_admin@your-domain.org \
     --organization-id=2
   ```

6. **Verify the application**
   
   ```bash
   curl https://your-domain.com
   ```

### What Each Command Does

| Command | Description |
|---------|-------------|
| `flask init-certs` | Generates X.509 certificate and private key for signing federation metadata. **Warning:** Regenerating will invalidate previously distributed public certificates. Prompts for confirmation if certificates exist. |
| `flask init-db` | **Drops all database tables and recreates them.** Prompts for confirmation if database exists. Creates default federation configuration, automatically creates a federation admin organization (Federation Admin Org) and admin user (fed@example.com / fedadmin). All existing data will be **permanently deleted**. Use with caution! |
| `flask createorganization` | Creates a new organization with specified type (federation_admin, full_member, or sp_member). Use this command to create additional organizations beyond the default one created by `init-db`. |
| `flask createuser` | Creates a new user and assigns appropriate roles based on organization type. Use this command to create additional users for testing or production environments. |

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

If the application fails to start, follow these steps:

1. **View container logs**
   ```bash
   # Find container ID
   docker ps -a | grep fedadmin
   
   # View logs (replace <container-id> with actual ID)
   docker logs <container-id>
   
   # Or use docker-compose
   docker-compose -f docker-compose.prod.yml logs web
   ```

2. **Common issues and solutions**
   
   | Error | Solution |
   |-------|----------|
   | `Port already in use` | Stop other services using port 5000, or change port in `docker-compose.prod.yml` |
   | `Permission denied` | Check file permissions, ensure running as correct user |
   | `Database locked` | Stop all containers, remove database file, reinitialize |

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