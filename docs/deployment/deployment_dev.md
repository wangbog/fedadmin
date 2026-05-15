# Setup Development Environment

Development environment uses a docker container (`Dockerfile`) that includes development tools and uses Flask's built-in development server (`flask run`). We use Visual Studio Code with the Dev Container extension to manage the development environment, which minimizes issues caused by environment inconsistencies.

### Important Information

- **Container User**: Runs as `fedadmin` user (UID/GID: 5000) for security
- **Volume Mapping**: `.` (project root) → `/app` (entire project is bind mounted, and WORKDIR is /app)
  - Storage path: `./app/storage/` (host) ↔ `/app/app/storage/` (container)
  - Database path: `./instance/fedadmin-dev.db` (host) ↔ `/app/instance/fedadmin-dev.db` (container)
  - Log path: `/var/log/fedadmin/` (only in container)

### Setup Steps

1. **Prepare the host system**

   **💡 Note:** Since our development environment is on Windows 11, this is the only host system we have tested. Windows do not need us to perform this step as Docker Desktop handles permissions automatically, if you're hosting on Linux/macOS, you may refer to below.
   
   > **Check if UID 5000 is available:**
   > ```bash
   > # Check if UID 5000 is already in use
   > getent passwd 5000
   > ```
   >
   > **💡 Note:** If UID 5000 conflicts, change it in:
   > - `Dockerfile` (line 16): `groupadd -g 5000` and `useradd -u 5000`
   > - `.devcontainer/devcontainer.json` (line 27 and 28): `"uid": "5000"` and `"gid": "5000"`

2. **Prepare configuration file**
   
   ```bash
   # Create .env file from template
   cp .env.dev.example .env
   ```

   > **⚠️ Important:** 
   > - You must change all REQUIRED values before building the docker image! 
   > - Always generate secure random keys using `openssl rand -hex 32`.
   > - The application requires email configuration for password recovery functionality. Without proper email configuration, the password recovery feature will not work.
   > - Any changes in this configuration file needs a container restart.

3. **Open the project in VS Code**
   - Open the project root in VS Code
   - Press `F1` and select "Dev Containers: Reopen in Container"
   - VS Code will build the image, start the container, and connect your workspace (first time may take a few minutes)
   - The Flask development server starts automatically when the container starts.

4. **Initialize database and certificates**
    
    After the container is ready, open the integrated terminal and run:

    ```bash
    # Generate signing certificates for SAML metadata
    flask init-certs
    
    # Create/update database tables using flask-migration
    flask db upgrade

    # Insert default data if tables are empty:
    # - Default roles (federation, full_member, sp_member)
    # - Federation configuration
    # - Federation Admin Org organization
    # - fedadmin user with randomly generated password (fed@example.com)
    flask init-db
    ```

    > **⚠️ Important:** The generated password will be shown on console, please keep it safe!

### Access the application

After completing the setup steps, verify everything is working:

1. Visit http://127.0.0.1:5000/
2. Try logging in with the federation admin account: `fed@example.com` / `the generated password`

### Daily Development

- **Edit code**: Modify files in VS Code, Flask auto-reloads automatically (FLASK_DEBUG=1)
- **Change dependencies**: 
  1. Edit `requirements.txt`
  2. Run `pip install -r requirements.txt` (temporary)
  3. Or rebuild container: Press `F1` → "Dev Containers: Rebuild Container" (permanent)
- **Change environment variables**: 
  1. Edit `.env` file
  2. Restart container: Press `F1` → "Dev Containers: Rebuild Container"
- **View application logs**:
  1. Using Docker logs: On your host machine, run `docker compose logs -f web` from the project root directory (where `docker-compose.yml` is located)
  2. Using log file: Application logs are also written to `/var/log/fedadmin/app.log` inside the container
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

2. **Reset and start over**
   - Press `F1` → "Dev Containers: Rebuild Container" to rebuild and restart