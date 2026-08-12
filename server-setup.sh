#!/bin/bash

set -e

if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run with root privileges (sudo)." >&2
    exit 1
fi

# 1. Create and configure 2GB Swap space
if [ ! -f /swapfile ]; then
    echo "Creating 2GB swap file..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    sysctl vm.swappiness=10
    echo 'vm.swappiness=10' >> /etc/sysctl.conf
else
    echo "Swap file already exists. Skipping."
fi

# 2. Update system and install required packages (including build tools for mysqlclient)
echo "Updating system packages..."
apt-get update
apt-get upgrade -y
apt-get install -y \
  build-essential certbot curl default-libmysqlclient-dev git nginx \
  pkg-config sqlite3 ufw python3 python3-pip python3-certbot-nginx python3-venv

# 3. Configure Firewall
echo "Configuring firewall..."
ufw allow 'Nginx Full'
ufw --force enable

# 4. Create application directory
APP_DIR="/var/www/moneylog3"
echo "Setting up application directory at $APP_DIR..."
mkdir -p "$APP_DIR"

TARGET_USER=${SUDO_USER:-root}
chown -R "$TARGET_USER":"$TARGET_USER" "$APP_DIR"

# 5. Initialize Python Virtual Environment and install requirements
echo "Creating Python virtual environment and installing packages..."
sudo -u "$TARGET_USER" python3 -m venv "$APP_DIR/venv"
if [ -f "$APP_DIR/requirements.txt" ]; then
    sudo -u "$TARGET_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip
    sudo -u "$TARGET_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"
    sudo -u "$TARGET_USER" "$APP_DIR/venv/bin/pip" install gunicorn
fi

if [ -f "$APP_DIR/manage.py" ]; then
    echo "Collecting static files..."
    sudo -u "$TARGET_USER" "$APP_DIR/venv/bin/python" "$APP_DIR/manage.py" collectstatic --noinput
fi

# 6. Configure Nginx
echo "Configuring Nginx..."
rm -f /etc/nginx/sites-enabled/default

cat << 'EOF' > /etc/nginx/sites-available/moneylog3
server {
    listen 80;
    server_name _ moneylog.duckdns.org;

    location /static/ {
        alias /var/www/moneylog3/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location / {
        include proxy_params;
        proxy_pass http://127.0.0.1:8000;
    }
}
EOF

ln -sf /etc/nginx/sites-available/moneylog3 /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# 7. Configure and start Gunicorn systemd service
echo "Configuring Gunicorn service..."
cat << EOF > /etc/systemd/system/gunicorn.service
[Unit]
Description=gunicorn daemon for moneylog3
After=network.target

[Service]
User=$TARGET_USER
Group=www-data
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/gunicorn \\
    --access-logfile - \\
    --workers 2 \\
    --bind 127.0.0.1:8000 \\
    core.wsgi:application

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl start gunicorn
systemctl enable gunicorn

certbot install --cert-name moneylog.duckdns.org -v

echo "Setup completed successfully."