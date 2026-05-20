# Setup Development Environment

Development environment uses a docker container (`Dockerfile`) that includes development tools and uses Flask's built-in development server (`flask run`). We use Visual Studio Code with the Dev Container extension to manage the development environment, which minimizes issues caused by environment inconsistencies.

## Important Information

- **Container User**: Runs as `fedadmin` user (UID/GID: 5000) for security
- **Volume Mapping**: `.` (project root) → `/app` (entire project is bind mounted, and WORKDIR is /app)
  - Storage path: `./app/storage/` (host) ↔ `/app/app/storage/` (container)
  - Database path: `./instance/fedadmin-dev.db` (host) ↔ `/app/instance/fedadmin-dev.db` (container)
  - Log path: `/var/log/fedadmin/` (only in container)

## Setup Steps

1. **Prepare the host system**

   **💡 Note:** Our development environment is on Windows 11, this is the only host system we have tested. However, VS Code with Dev Containers should also work on Linux with GUI and MacOS, but you should pay attention to the user/group management on these platforms.

   **⚠️ Important:** The docker container runs as the `fedadmin` user with UID 5000. Docker Desktop on Windows does not require any special steps, as it handles permissions automatically. If you are hosting on Linux/macOS, you need to ensure that a fedadmin user with UID 5000 has been created on the host system beforehand. Please refer to [1. Prepare the host system](deployment_prod.md#1-prepare-the-host-system).

2. **Prepare configuration file**

   ```bash
   # Create .env file from template
   cp .env.dev.example .env
   ```

   **⚠️ Important:** 
   - You must change all REQUIRED values before building the docker image! 
   - Always generate secure random keys using `openssl rand -hex 32`.
   - The application requires email configuration for password recovery functionality. Without proper email configuration, the password recovery feature will not work.
   - Any changes in this configuration file needs a container restart.

3. **Open the project in VS Code**
   - Open the project root in VS Code
   - Press `F1` and select "Dev Containers: Reopen in Container"
   - VS Code will build the image, start the container, and connect your workspace (first time may take a few minutes)
   - The Flask development server starts automatically when the container starts.

4. **Initialize federation metadata certificates and database**

   After the container is ready, open the integrated terminal (already inside the container) and run:

   ```bash
   # Generate signing certificates for SAML metadata
   flask init-certs

   # Create/update database tables using Flask-Migrate
   flask db upgrade

   # Insert default data if tables are empty:
   # - Default roles (federation, full_member, sp_member)
   # - Federation configuration
   # - Federation Admin Org organization
   # - fedadmin user with randomly generated password (fed@example.com)
   flask init-db
   ```

   **⚠️ Important:** The generated password will be shown on console, please keep it safe!

   Check the files are generated in the integrated terminal (already inside the container):

   ```bash
   # Check the generated files
   fedadmin ➜ /app (main) $ ls app/storage/private/federation/
   fed.crt  fed.key

   fedadmin ➜ /app (main) $ ls instance/
   fedadmin-dev.db
   ```

## Access the application

After completing the setup steps, verify everything is working:

1. Visit http://127.0.0.1:5000/
2. Try logging in with the federation admin account: `fed@example.com` / `the generated password`

## Scheduled Tasks

See [Scheduled Tasks](scheduled_tasks.md) to understand the scheduled tasks.

Since the host Windows 11 development environments don't have crontab, you can execute commands in the integrated terminal (already inside the container) on-demand:

   ```bash
   # Regenerate metadata
   flask regenerate-metadata

   # Check eduGAIN updates
   flask check-edugain-updates
   ```

## Daily Development

- **Edit code**: Modify files in VS Code, Flask auto-reloads automatically (FLASK_DEBUG=1)
- **Change dependencies**: 
  1. Edit `requirements.txt`
  2. Run `pip install -r requirements.txt` (temporary)
  3. Or rebuild container: Press `F1` → "Dev Containers: Rebuild Container" (permanent)
- **Change environment variables**: 
  1. Edit `.env` file
  2. Restart container: Press `F1` → "Dev Containers: Rebuild Container"
- **View application logs**:
  1. Using Docker logs: On your host machine, run `docker compose logs -f web` from the project root directory (where `docker-compose.yml` is located).
  2. Using log file: Application logs are also written to `/var/log/fedadmin/app.log` inside the container.
- **Stop container**: Close VS Code window; it will automatically reconnect next time you open it

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
   - Press `F1` → "Dev Containers: Rebuild Container" to rebuild and restart
