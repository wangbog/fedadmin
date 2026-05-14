# Setup Development Environment

Development environment uses a separate Dockerfile (`Dockerfile`) that includes development tools and uses Flask's built-in development server (`flask run`). We use Visual Studio Code with the Dev Container extension to manage the development environment, which minimizes issues caused by environment inconsistencies.

### Important Information

- **Container User**: Runs as `fedadmin` user (UID/GID: 5000) for security
- **Volume Mapping**: `.` (project root) → `/app` (entire project is bind mounted)
  - Code changes take effect immediately (Flask auto-reloads)
  - Dependency or environment variable changes require container rebuild (see Daily Development)
  - Storage path: `./storage/` (host) ↔ `/app/storage/` (container)
  - Database path: `./instance/fedadmin.db` (host) ↔ `/app/instance/fedadmin.db` (container)
- **Backup**: Regularly backup `./instance/` and `./storage/` directories

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
   > - `Dockerfile` (line 16): `groupadd -g 5000` and `useradd -u 5000`
   > - This README (update all UID/GID references)
   >
   > **💡 Tip:** Windows users do not need to perform this step as Docker Desktop handles permissions automatically.

2. **Prepare configuration file**
   
   ```bash
   # Create .env file from template
   cp .env.dev.example .env
   
   # Edit .env and replace placeholder values with your actual configuration
   ```

   > **💡 Tip:** The `.env.dev.example` file contains development-friendly default values. You can edit `.env` to customize your configuration before opening the container.
   >
   > **⚠️ Important:** The application requires email configuration for password recovery functionality. Before deploying, you must configure the mail server settings in your `.env` file. Without proper email configuration, the password recovery feature will not work.

3. **Open the project in VS Code**
   - Open the project root in VS Code
   - Press `F1` and select "Dev Containers: Reopen in Container"
   - VS Code will build the image, start the container, and connect your workspace (first time may take a few minutes)

4. **Initialize certificates and database**
   
   After the container is ready, open the integrated terminal and run:

   > **⚠ Important:** These commands will prompt for confirmation if files already exist. Regenerating certificates will invalidate any previously distributed public certificates! Initializing the database will delete all existing data!

   ```bash
   # Generate signing certificates for SAML metadata
   flask init-certs
   
   # Initialize database, create default federation configuration, and automatically create:
   # - Federation Admin Org organization
   # - fedadmin user (fed@example.com / fedadmin)
   flask init-db
   ```

5. **Create additional test data (optional)**
   
   The `init-db` command automatically creates the minimal required test data. If you need additional organizations or users for testing, you can use these commands:

   ```bash
   # Create additional test organizations
   flask createorganization --name="Test Member Org" --description="A test member organization." --type=full_member --url="https://example.org"
   
   # Create additional test users
   flask createuser --username=testuser --email=test@example.org --organization-id=2
   ```

6. **Access the application**
   
   The Flask development server starts automatically when the container starts.
   - URL: http://127.0.0.1:5000/
   - Test accounts (login with email):
     - Federation Admin: `fed@example.com` / `fedadmin`

### What Each Command Does

| Command | Description |
|---------|-------------|
| `flask init-certs` | Generates X.509 certificate and private key for signing federation metadata. **Warning:** Regenerating will invalidate previously distributed public certificates. Prompts for confirmation if certificates exist. |
| `flask init-db` | **Drops all database tables and recreates them.** Prompts for confirmation if database exists. Creates default federation configuration, automatically creates a federation admin organization (Federation Admin Org) and admin user (fed@example.com / fedadmin). All existing data will be **permanently deleted**. Use with caution! |
| `flask createorganization` | Creates a new organization with specified type (federation_admin, full_member, or sp_member). Use this command to create additional organizations beyond the default one created by `init-db`. |
| `flask createuser` | Creates a new user and assigns appropriate roles based on organization type. Use this command to create additional users for testing or production environments. |

### Daily Development

- **Edit code**: Modify files in VS Code, Flask auto-reloads automatically (FLASK_DEBUG=1)
- **Run CLI commands**: Execute directly in the terminal (already inside container)
  ```bash
  # List all available Flask commands
  flask --list-commands
  ```
- **Add dependencies**: 
  1. Edit `requirements.txt`
  2. Run `pip install -r requirements.txt` (temporary)
  3. Or rebuild container: Press `F1` → "Dev Containers: Rebuild Container" (permanent)
- **Change environment variables**: 
  1. Edit `.env` file
  2. Restart container: Press `F1` → "Dev Containers: Rebuild Container"
- **View application logs**:
  1.  Using Docker logs: On your host machine, run `docker compose logs web -f` from the project root directory (where `docker-compose.yml` is located). This shows the Flask development server's stdout/stderr output.
  2.  Using log file: Application logs are also written to `/var/log/fedadmin/app.log` inside the container.
- **Stop container**: Close VS Code window; it will automatically reconnect next time you open it

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
   | `Module not found` | Rebuild container: `F1` → "Dev Containers: Rebuild Container" |
   | `Port already in use` | Stop other services using port 5000, or change port in `docker-compose.yml` |
   | `Permission denied` | Check file permissions, or run VS Code as administrator |

3. **Reset and start over**
   - Press `F1` → "Dev Containers: Rebuild Container" to rebuild and restart
   
   - Or using command line:
   ```bash
   # Stop and remove container
   docker-compose down
   
   # Rebuild and restart
   docker-compose up -d --build