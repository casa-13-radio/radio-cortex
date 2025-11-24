#!/bin/bash
set -e

# =============================================================================
# Radio Cortex - Deploy Script
# =============================================================================
# Usage: ./scripts/deploy.sh [staging|production]
#
# This script deploys the application to the specified environment.
# =============================================================================

ENVIRONMENT=${1:-staging}
APP_DIR="/opt/radio-cortex"
BACKUP_DIR="$APP_DIR/backups"
LOG_FILE="$APP_DIR/logs/deploy.log"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a $LOG_FILE
}

success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a $LOG_FILE
}

error() {
    echo -e "${RED}❌ $1${NC}" | tee -a $LOG_FILE
    exit 1
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a $LOG_FILE
}

# =============================================================================
# PRE-FLIGHT CHECKS
# =============================================================================

log "Starting deploy to $ENVIRONMENT"

# Check if running in correct directory
if [ ! -d "$APP_DIR/.git" ]; then
    error "Not in application directory. Expected: $APP_DIR"
fi

cd $APP_DIR

# Check if environment is valid
if [ "$ENVIRONMENT" != "staging" ] && [ "$ENVIRONMENT" != "production" ]; then
    error "Invalid environment: $ENVIRONMENT. Use 'staging' or 'production'"
fi

# Check if .env file exists
if [ ! -f "$APP_DIR/.env" ]; then
    error ".env file not found. Run setup_server.sh first"
fi

# =============================================================================
# BACKUP (Production only)
# =============================================================================

if [ "$ENVIRONMENT" = "production" ]; then
    log "Creating backup..."
    mkdir -p $BACKUP_DIR
    
    # Backup database
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"
    
    docker-compose exec -T postgres pg_dump -U cortex radiocortex | gzip > $BACKUP_FILE
    
    if [ -f "$BACKUP_FILE" ]; then
        success "Database backup created: $BACKUP_FILE"
    else
        error "Database backup failed"
    fi
    
    # Keep only last 30 days of backups
    find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete
fi

# =============================================================================
# GIT PULL
# =============================================================================

log "Pulling latest code from Git..."

# Determine which branch to use
if [ "$ENVIRONMENT" = "staging" ]; then
    BRANCH="develop"
else
    BRANCH="main"
fi

# Stash local changes if any
git stash

# Pull latest code
git fetch origin
git checkout $BRANCH
git pull origin $BRANCH

success "Code updated to latest $BRANCH"

# =============================================================================
# BUILD DOCKER IMAGES
# =============================================================================

log "Building Docker images..."

if [ "$ENVIRONMENT" = "production" ]; then
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache
else
    docker-compose build
fi

success "Docker images built"

# =============================================================================
# RUN DATABASE MIGRATIONS
# =============================================================================

log "Running database migrations..."

docker-compose run --rm cortex alembic upgrade head

success "Database migrations completed"

# =============================================================================
# RESTART SERVICES (Zero-downtime for production)
# =============================================================================

log "Restarting services..."

if [ "$ENVIRONMENT" = "production" ]; then
    # Zero-downtime restart for production
    log "Performing zero-downtime restart..."
    
    # Start new containers without stopping old ones
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps --scale cortex=2 cortex
    
    # Wait for new containers to be healthy
    log "Waiting for new containers to be healthy..."
    sleep 15
    
    # Check if new containers are healthy
    if curl -f http://localhost:8000/health; then
        success "New containers are healthy"
        
        # Scale down old containers
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps --scale cortex=1 cortex
        
        # Restart other services
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
    else
        error "New containers failed health check. Rolling back..."
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps --scale cortex=1 cortex
        error "Rollback completed. Check logs for errors."
    fi
else
    # Simple restart for staging
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
fi

success "Services restarted"

# =============================================================================
# POST-DEPLOY CHECKS
# =============================================================================

log "Running post-deploy checks..."

# Wait for services to stabilize
sleep 10

# Check if API is responding
if curl -f http://localhost:8000/health; then
    success "API health check passed"
else
    error "API health check failed"
fi

# Check if database is accessible
if docker-compose exec -T postgres pg_isready -U cortex; then
    success "Database is accessible"
else
    warning "Database check failed"
fi

# Check if Redis is accessible
if docker-compose exec -T redis redis-cli ping | grep -q PONG; then
    success "Redis is accessible"
else
    warning "Redis check failed"
fi

# =============================================================================
# CLEANUP
# =============================================================================

log "Cleaning up..."

# Remove dangling images
docker image prune -f

# Remove old logs (keep last 7 days)
find $APP_DIR/logs -name "*.log" -mtime +7 -delete

success "Cleanup completed"

# =============================================================================
# SUMMARY
# =============================================================================

echo ""
echo "======================================"
echo "  Deploy to $ENVIRONMENT completed!"
echo "======================================"
echo ""
echo "📊 Deployment Summary:"
echo "   Environment: $ENVIRONMENT"
echo "   Branch: $BRANCH"
echo "   Commit: $(git rev-parse --short HEAD)"
echo "   Time: $(date)"
echo ""
echo "🔍 Check deployment:"
echo "   curl http://localhost:8000/health"
echo "   docker-compose logs -f"
echo ""
echo "📝 Logs available at: $LOG_FILE"
echo ""

success "Deploy completed successfully! 🎉"