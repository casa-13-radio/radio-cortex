#!/bin/bash
set -e

# =============================================================================
# Radio Cortex - Server Setup Script
# =============================================================================
# Usage: ./scripts/setup_server.sh [staging|production]
#
# This script should be run ONCE on a fresh server to set up the environment.
# =============================================================================

ENVIRONMENT=${1:-staging}
APP_DIR="/opt/radio-cortex"
APP_USER="cortex"

echo "🚀 Setting up Radio Cortex - Environment: $ENVIRONMENT"

# =============================================================================
# 1. SYSTEM UPDATES
# =============================================================================
echo "📦 Updating system packages..."
sudo apt update
sudo apt upgrade -y

# =============================================================================
# 2. INSTALL DEPENDENCIES
# =============================================================================
echo "📦 Installing dependencies..."
sudo apt install -y \
    docker.io \
    docker-compose \
    git \
    curl \
    nginx \
    certbot \
    python3-certbot-nginx \
    ufw \
    fail2ban \
    htop \
    vim

# =============================================================================
# 3. CREATE APPLICATION USER
# =============================================================================
echo "👤 Creating application user..."
if ! id "$APP_USER" &>/dev/null; then
    sudo adduser --system --group --home $APP_DIR $APP_USER
    echo "✅ User $APP_USER created"
else
    echo "ℹ️  User $APP_USER already exists"
fi

# Add user to docker group
sudo usermod -aG docker $APP_USER

# =============================================================================
# 4. SETUP APPLICATION DIRECTORY
# =============================================================================
echo "📁 Setting up application directory..."
sudo mkdir -p $APP_DIR
sudo chown -R $APP_USER:$APP_USER $APP_DIR

# =============================================================================
# 5. CLONE REPOSITORY
# =============================================================================
echo "📥 Cloning repository..."
cd /tmp
if [ ! -d "$APP_DIR/.git" ]; then
    sudo -u $APP_USER git clone https://github.com/yourusername/radio-cortex.git $APP_DIR
    echo "✅ Repository cloned"
else
    echo "ℹ️  Repository already exists"
fi

# =============================================================================
# 6. SETUP ENVIRONMENT VARIABLES
# =============================================================================
echo "🔧 Setting up environment variables..."
if [ ! -f "$APP_DIR/.env" ]; then
    sudo -u $APP_USER cp $APP_DIR/.env.example $APP_DIR/.env
    echo "⚠️  Please edit $APP_DIR/.env with your configuration"
    echo "⚠️  Required variables: DATABASE_URL, GROQ_API_KEY, SECRET_KEY, etc."
else
    echo "ℹ️  .env file already exists"
fi

# =============================================================================
# 7. SETUP NGINX
# =============================================================================
echo "🌐 Configuring Nginx..."
DOMAIN=$(grep "DOMAIN=" $APP_DIR/.env 2>/dev/null | cut -d'=' -f2 || echo "example.com")

sudo tee /etc/nginx/sites-available/radio-cortex <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Health check endpoint
    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/radio-cortex /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo "✅ Nginx configured"

# =============================================================================
# 8. SETUP SSL (Let's Encrypt)
# =============================================================================
if [ "$ENVIRONMENT" = "production" ]; then
    echo "🔒 Setting up SSL certificate..."
    sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN
    echo "✅ SSL certificate installed"
else
    echo "ℹ️  Skipping SSL for staging (use self-signed or Cloudflare)"
fi

# =============================================================================
# 9. SETUP FIREWALL
# =============================================================================
echo "🔥 Configuring firewall..."
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
echo "✅ Firewall configured"

# =============================================================================
# 10. SETUP DOCKER
# =============================================================================
echo "🐳 Starting Docker services..."
cd $APP_DIR
sudo -u $APP_USER docker-compose up -d postgres redis rabbitmq

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# =============================================================================
# 11. INITIALIZE DATABASE
# =============================================================================
echo "💾 Initializing database..."
sudo -u $APP_USER docker-compose run --rm cortex alembic upgrade head
echo "✅ Database initialized"

# =============================================================================
# 12. SETUP SYSTEMD SERVICES
# =============================================================================
echo "🔧 Setting up systemd services..."

# Cortex API service
sudo tee /etc/systemd/system/radio-cortex.service <<EOF
[Unit]
Description=Radio Cortex API
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/docker-compose -f $APP_DIR/docker-compose.yml -f $APP_DIR/docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker-compose -f $APP_DIR/docker-compose.yml -f $APP_DIR/docker-compose.prod.yml down
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable radio-cortex
sudo systemctl start radio-cortex

echo "✅ Systemd services configured"

# =============================================================================
# 13. SETUP BACKUP CRON JOB
# =============================================================================
echo "💾 Setting up backup cron job..."
sudo -u $APP_USER crontab -l > /tmp/cortex-cron 2>/dev/null || true
echo "0 2 * * * $APP_DIR/scripts/backup.sh >> $APP_DIR/logs/backup.log 2>&1" >> /tmp/cortex-cron
sudo -u $APP_USER crontab /tmp/cortex-cron
rm /tmp/cortex-cron
echo "✅ Backup cron job configured"

# =============================================================================
# 14. FINAL CHECKS
# =============================================================================
echo "🔍 Running final checks..."

# Check if services are running
docker ps

# Check if API is responding
sleep 5
curl -f http://localhost:8000/health || echo "⚠️  API health check failed"

# =============================================================================
# DONE
# =============================================================================
echo ""
echo "✅ ======================================"
echo "✅  Server setup complete!"
echo "✅ ======================================"
echo ""
echo "📝 Next steps:"
echo "   1. Edit $APP_DIR/.env with your API keys"
echo "   2. Restart services: sudo systemctl restart radio-cortex"
echo "   3. Check logs: docker-compose logs -f"
echo "   4. Verify health: curl http://localhost:8000/health"
echo ""
echo "🌐 Access your app at: http://$DOMAIN"
echo ""