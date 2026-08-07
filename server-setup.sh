#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# 1. Create and configure 2GB Swap space
if [ ! -f /swapfile ]; then
    echo "Creating 2GB swap file..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    
    # Make swap permanent
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    
    # Adjust swappiness for better performance on servers
    sysctl vm.swappiness=10
    echo 'vm.swappiness=10' >> /etc/sysctl.conf
    
    echo "Swap configured successfully."
else
    echo "Swap file already exists. Skipping."
fi

# 2. Update system and install required packages
echo "Updating system packages..."
apt-get update
apt-get upgrade -y

echo "Installing Python, SQLite, Nginx, and Git..."
# We include python3-venv for virtual environment creation
apt-get install -y python3 python3-pip python3-venv sqlite3 nginx git curl

# 3. Create application directory
APP_DIR="/var/www/moneylog3"
echo "Setting up application directory at $APP_DIR..."
mkdir -p "$APP_DIR"

# Change ownership to the current user (if run with sudo, changes to the invoking user)
# If run as root, it stays root. Adjust as necessary for your deployment user.
TARGET_USER=${SUDO_USER:-root}
chown -R "$TARGET_USER":"$TARGET_USER" "$APP_DIR"

# 4. Initialize Python Virtual Environment
echo "Creating Python virtual environment..."
sudo -u "$TARGET_USER" python3 -m venv "$APP_DIR/venv"

echo "Setup complete. You can now clone your Django Unfold project into $APP_DIR and activate the virtual environment using: source $APP_DIR/venv/bin/activate"
