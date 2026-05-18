# Gunicorn configuration for production environment

# Worker settings
workers = 4
threads = 2
worker_class = "sync"
max_requests = 1000
max_requests_jitter = 50
timeout = 120
keepalive = 5

# Connection settings
limit_request_line = 4096
limit_request_field_size = 8190
limit_request_fields = 100
backlog = 2048

# Logging settings
accesslog = "/var/log/fedadmin/access.log"
errorlog = "/var/log/fedadmin/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process management
daemon = False

# Server binding
bind = "0.0.0.0:5000"
chdir = "/app"

# Security settings
secure_scheme_headers = {"X-Forwarded-Proto": "https"}
forwarded_allow_ips = "*"
