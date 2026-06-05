# Production Deployment Without Docker

This guide describes a production deployment that runs FedAdmin directly on a Linux server without Docker. The recommended production path is still the Docker-based guide in [Production Deployment](deployment_prod.md), because it provides a controlled runtime environment. Use this non-Docker guide when your deployment policy requires system packages, a Python virtual environment, systemd, and Nginx on the host server.

## Important Information

- **Host platform**: Linux server only. This guide is not intended for Windows or macOS production hosts.
- **Application user**: Runs as a dedicated `fedadmin` system user.
- **Project root**: `/data/fedadmin`
- **Python environment**: `/data/fedadmin/.venv`
- **Storage path**: `/data/fedadmin/app/storage/`
- **Database path**: `/data/fedadmin/instance/fedadmin-prod.db`
- **Log path**: `/var/log/fedadmin/`
- **Process manager**: systemd starts and supervises Gunicorn.
- **Reverse proxy**: Nginx terminates HTTPS and exposes public metadata files.
- **Backup**: Regularly back up:
  - `/data/fedadmin/instance/`
  - `/data/fedadmin/app/storage/`
  - `/var/log/fedadmin/`
  - `/data/fedadmin/.env`

## Setup Steps

1. **Install system dependencies**

   Install Python 3.12, build tools, XML libraries, file type detection libraries, and Nginx. Package names differ by distribution.

   Debian/Ubuntu example:

   ```bash
   sudo apt-get update
   sudo apt-get install -y \
       python3.12 python3.12-venv python3.12-dev \
       build-essential pkg-config \
       libxml2-dev libxslt1-dev libyaml-dev libmagic1 \
       libxmlsec1-dev xmlsec1 \
       sqlite3 nginx
   ```

   RHEL/Rocky/AlmaLinux example:

   ```bash
   sudo dnf install -y \
       python3.12 python3.12-devel python3.12-pip \
       gcc gcc-c++ make pkgconf-pkg-config \
       libxml2-devel libxslt-devel libyaml-devel file-libs \
       xmlsec1 xmlsec1-devel xmlsec1-openssl \
       sqlite nginx
   ```

   If your distribution does not provide Python 3.12 packages, install Python 3.12 through your platform's supported method before continuing.

2. **Create the application user and directories**

   ```bash
   sudo groupadd --system fedadmin
   sudo useradd --system --gid fedadmin --home-dir /data/fedadmin --shell /bin/bash fedadmin

   sudo mkdir -p /data/fedadmin
   sudo mkdir -p /var/log/fedadmin
   sudo chown -R fedadmin:fedadmin /data/fedadmin /var/log/fedadmin
   sudo chmod 750 /data/fedadmin /var/log/fedadmin
   ```

3. **Copy or clone the project**

   Copy the FedAdmin project files into `/data/fedadmin`, or clone the repository there.

   ```bash
   sudo -u fedadmin git clone <your-fedadmin-repository-url> /data/fedadmin
   ```

   If the project files are copied by another user, reset ownership afterwards:

   ```bash
   sudo chown -R fedadmin:fedadmin /data/fedadmin
   ```

4. **Create the Python virtual environment and install dependencies**

   ```bash
   sudo -u fedadmin bash -lc '
     cd /data/fedadmin
     python3.12 -m venv .venv
     . .venv/bin/activate
     python -m pip install --upgrade pip wheel setuptools
     python -m pip install --no-cache-dir -r requirements.txt
   '
   ```

   Verify key runtime dependencies:

   ```bash
   sudo -u fedadmin bash -lc '
     cd /data/fedadmin
     . .venv/bin/activate
     python -c "import flask, xmlsec, magic, lxml; print(\"Python imports OK\")"
     pyff --version
   '
   ```

5. **Prepare runtime directories**

   ```bash
   sudo -u fedadmin mkdir -p /data/fedadmin/instance
   sudo -u fedadmin mkdir -p /data/fedadmin/app/storage/public/federation
   sudo -u fedadmin mkdir -p /data/fedadmin/app/storage/private/federation
   sudo chmod 750 /data/fedadmin/instance /data/fedadmin/app/storage
   ```

6. **Prepare the configuration file**

   ```bash
   sudo -u fedadmin bash -lc '
     cd /data/fedadmin
     cp .env.prod.example .env
     chmod 600 .env
   '
   ```

   Edit `/data/fedadmin/.env` and replace all required values.

   ```bash
   sudo -u fedadmin nano /data/fedadmin/.env
   ```

   Important notes:

   - Keep `FLASK_CONFIG=production`.
   - Generate strong random values with `openssl rand -hex 32` for `SECRET_KEY` and `SECURITY_PASSWORD_SALT`.
   - Configure a reliable SMTP provider. FedAdmin uses email for password recovery, password change notices, and new-user password setup links.
   - SMTP delivery failures are recorded in `Federation Admin/System/Email Delivery`; they do not cancel the related account action. For newly created administrators, administrators can copy the setup/reset link shown once after account creation.
   - Use `MAIL_SUPPRESS_SEND=True` only for temporary maintenance or controlled testing.
   - Keep `LOG_FILE=/var/log/fedadmin/app.log` unless you have a specific logging policy.
   - Any changes in this configuration file require restarting the systemd service after it is created.

7. **Configure Gunicorn**

   Create a host-specific Gunicorn configuration. This avoids using the Docker config's `/app` working directory.

   ```bash
   sudo tee /etc/fedadmin-gunicorn.conf.py >/dev/null <<'EOF'
   workers = 4
   threads = 2
   worker_class = "sync"
   max_requests = 1000
   max_requests_jitter = 50
   timeout = 120
   keepalive = 5

   limit_request_line = 4096
   limit_request_field_size = 8190
   limit_request_fields = 100
   backlog = 2048

   accesslog = "/var/log/fedadmin/access.log"
   errorlog = "/var/log/fedadmin/error.log"
   loglevel = "info"
   access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

   daemon = False
   bind = "127.0.0.1:5000"
   chdir = "/data/fedadmin"

   secure_scheme_headers = {"X-Forwarded-Proto": "https"}
   forwarded_allow_ips = "127.0.0.1"
   EOF

   sudo chmod 644 /etc/fedadmin-gunicorn.conf.py
   ```

8. **Create the systemd service**

   ```bash
   sudo tee /etc/systemd/system/fedadmin.service >/dev/null <<'EOF'
   [Unit]
   Description=FedAdmin Gunicorn Service
   After=network.target

   [Service]
   Type=simple
   User=fedadmin
   Group=fedadmin
   WorkingDirectory=/data/fedadmin
   EnvironmentFile=/data/fedadmin/.env
   Environment=PYTHONUNBUFFERED=1
   RuntimeDirectory=pyff
   ExecStart=/data/fedadmin/.venv/bin/gunicorn run:app -c /etc/fedadmin-gunicorn.conf.py
   Restart=on-failure
   RestartSec=5
   PrivateTmp=true
   NoNewPrivileges=true

   [Install]
   WantedBy=multi-user.target
   EOF

   sudo systemctl daemon-reload
   ```

9. **Configure Nginx reverse proxy**

   For production deployment, use HTTPS in front of Gunicorn. The `X-Forwarded-Proto` header is required so Flask can detect HTTPS and handle secure cookies correctly.

   Example Nginx server block:

   ```nginx
   server {
       listen 80;
       server_name <your-hostname>;
       return 301 https://$host$request_uri;
   }

   server {
       listen 443 ssl http2;
       server_name <your-hostname>;

       ssl_certificate /path/to/fullchain.pem;
       ssl_certificate_key /path/to/privkey.pem;

       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       location ^~ /public/ {
           alias /data/fedadmin/app/storage/public/;
           add_header Cache-Control "public, max-age=300";
       }
   }
   ```

   Because `/data/fedadmin` is restricted, make sure the Nginx worker user can traverse the public storage path. For example, if Nginx runs as `nginx`:

   ```bash
   sudo usermod -aG fedadmin nginx
   sudo systemctl restart nginx
   ```

   On Debian/Ubuntu, the Nginx user is often `www-data`:

   ```bash
   sudo usermod -aG fedadmin www-data
   sudo systemctl restart nginx
   ```

   If you temporarily test without HTTPS, production secure cookies will not work over plain HTTP. For real production, keep HTTPS enabled rather than weakening `SESSION_COOKIE_SECURE`.

10. **Initialize certificates, database, and metadata files**

    Federation metadata signing requires `app/storage/private/federation/fed.crt` and `app/storage/private/federation/fed.key` before metadata is generated. For production, use your federation signing certificate whenever possible.

    Place your own certificate and key:

    ```bash
    sudo -u fedadmin cp /path/to/fed.crt /data/fedadmin/app/storage/private/federation/fed.crt
    sudo -u fedadmin cp /path/to/fed.key /data/fedadmin/app/storage/private/federation/fed.key
    sudo chmod 600 /data/fedadmin/app/storage/private/federation/fed.key
    ```

    If you do not have a certificate yet, `flask init-certs` can generate a default self-signed certificate, but its fixed parameters may not match your federation policy and should be reviewed or replaced before production use.

    Run initialization commands from the project root:

    ```bash
    sudo -u fedadmin bash -lc '
      cd /data/fedadmin
      . .venv/bin/activate

      # Optional fallback: generate a default self-signed signing certificate
      flask init-certs

      # Create/update database tables using Flask-Migrate
      flask db upgrade

      # Insert default roles, federation configuration, FEDERATION_ADMIN organization,
      # and the initial fed@example.com administrator account if tables are empty.
      flask init-db

      # Generate initial federation metadata files
      flask regenerate-metadata
    '
    ```

    **Important:** The generated password from `flask init-db` is shown in the console. Save it securely.

    The generated federation registration and publisher URLs, and any certificate generated by `flask init-certs`, are example defaults. Replace them with real federation values before production use.

    Expected files include:

    ```text
    /data/fedadmin/app/storage/private/federation/fed.crt
    /data/fedadmin/app/storage/private/federation/fed.key
    /data/fedadmin/app/storage/public/federation/fed-metadata.xml
    /data/fedadmin/app/storage/public/federation/fed-metadata-edugain.xml
    /data/fedadmin/app/storage/public/federation/fed-metadata-beta.xml
    /data/fedadmin/instance/fedadmin-prod.db
    ```

11. **Start FedAdmin**

    ```bash
    sudo systemctl enable --now fedadmin
    sudo systemctl status fedadmin
    ```

    Check logs:

    ```bash
    sudo journalctl -u fedadmin -f
    sudo tail -f /var/log/fedadmin/app.log
    sudo tail -f /var/log/fedadmin/error.log
    ```

## Access the Application

1. Visit `https://<host>/`.
2. Log in with `fed@example.com` and the password generated by `flask init-db`.
3. Change the initial administrator password after first login.

Example public metadata URLs:

```text
https://<host>/public/federation/fed-metadata.xml
https://<host>/public/federation/fed-metadata-edugain.xml
https://<host>/public/federation/fed-metadata-beta.xml
```

## Scheduled Tasks

See [Scheduled Tasks](scheduled_tasks.md) for task behavior details.

Configure crontab as the `fedadmin` user:

```bash
sudo -u fedadmin mkdir -p /data/fedadmin/data/host_logs
sudo -u fedadmin crontab -e
```

Add crontab rules:

```cron
30 2 * * * cd /data/fedadmin && . .venv/bin/activate && flask regenerate-metadata >> /data/fedadmin/data/host_logs/cron.log 2>&1
15 * * * * cd /data/fedadmin && . .venv/bin/activate && flask check-edugain-updates >> /data/fedadmin/data/host_logs/cron.log 2>&1
```

Configure logrotate for `/data/fedadmin/data/host_logs/cron.log` and `/var/log/fedadmin/*.log` according to your operational policy.

## Operational Tasks

- **Restart after configuration changes**:

  ```bash
  sudo systemctl restart fedadmin
  ```

- **View service status**:

  ```bash
  sudo systemctl status fedadmin
  ```

- **View logs**:

  ```bash
  sudo journalctl -u fedadmin -f
  sudo tail -f /var/log/fedadmin/app.log
  sudo tail -f /var/log/fedadmin/access.log
  sudo tail -f /var/log/fedadmin/error.log
  ```

- **Run Flask commands manually**:

  ```bash
  sudo -u fedadmin bash -lc '
    cd /data/fedadmin
    . .venv/bin/activate
    flask --help
  '
  ```

- **Upgrade application code**:

  ```bash
  sudo systemctl stop fedadmin

  sudo -u fedadmin bash -lc '
    cd /data/fedadmin
    git pull
    . .venv/bin/activate
    python -m pip install --no-cache-dir -r requirements.txt
    flask db upgrade
    flask regenerate-metadata
  '

  sudo systemctl start fedadmin
  ```

## Troubleshooting

1. **Gunicorn does not start**

   ```bash
   sudo systemctl status fedadmin
   sudo journalctl -u fedadmin -n 100
   sudo tail -n 100 /var/log/fedadmin/error.log
   ```

   Common causes include missing required `.env` values, wrong file permissions, missing system libraries, or an unavailable port.

2. **Login fails behind HTTPS**

   Confirm that Nginx sends `X-Forwarded-Proto`:

   ```nginx
   proxy_set_header X-Forwarded-Proto $scheme;
   ```

   Production mode uses secure cookies, so plain HTTP access is not suitable for production login.

3. **Metadata URLs are not accessible**

   Check the Nginx `/public/` alias and directory traversal permissions:

   ```bash
   ls -ld /data /data/fedadmin /data/fedadmin/app /data/fedadmin/app/storage /data/fedadmin/app/storage/public
   sudo nginx -t
   sudo systemctl reload nginx
   ```

4. **Python package installation fails**

   Verify system development libraries are installed, especially `libxml2`, `libxslt`, `libyaml`, `libmagic`, `xmlsec1`, and Python development headers.

5. **Metadata signing fails**

   Verify the signing key and certificate:

   ```bash
   sudo -u fedadmin test -r /data/fedadmin/app/storage/private/federation/fed.crt
   sudo -u fedadmin test -r /data/fedadmin/app/storage/private/federation/fed.key
   sudo -u fedadmin bash -lc 'cd /data/fedadmin && . .venv/bin/activate && flask regenerate-metadata'
   ```
