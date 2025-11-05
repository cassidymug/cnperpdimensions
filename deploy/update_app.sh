#!/bin/bash
# CNPERP Application Update Script for Linux/Ubuntu
# Usage: ./update_app.sh

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_ENABLED=true
RESTART_ENABLED=true
SERVICE_NAME="cnperp"  # systemd service name

echo -e "${CYAN}"
echo "========================================"
echo "🔄 CNPERP Application Update Script"
echo "========================================"
echo -e "${NC}"

# Navigate to app directory
cd "$APP_ROOT"
echo -e "${YELLOW}📁 Working directory: $APP_ROOT${NC}"

# Check if git repository
if [ ! -d ".git" ]; then
    echo -e "${RED}❌ Error: Not a git repository!${NC}"
    echo -e "${YELLOW}Run: git init && git remote add origin https://github.com/cassidymug/cnperp-python.git${NC}"
    exit 1
fi

# Backup database
if [ "$BACKUP_ENABLED" = true ]; then
    echo -e "${YELLOW}💾 Creating database backup...${NC}"
    source .venv/bin/activate
    python -c "from app.services.backup_service import BackupService; from app.core.database import SessionLocal; db = SessionLocal(); BackupService(db).create_backup('pre_update'); db.close()" || echo -e "${YELLOW}⚠️  Backup failed, continuing...${NC}"
    echo -e "${GREEN}✅ Database backup completed${NC}"
fi

# Stash local changes
echo -e "\n${YELLOW}📦 Stashing local changes...${NC}"
git stash push -m "Auto-stash before update $(date '+%Y-%m-%d %H:%M:%S')"

# Fetch latest changes
echo -e "${YELLOW}🌐 Fetching from remote...${NC}"
git fetch origin

# Show changes
CURRENT_BRANCH=$(git branch --show-current)
echo -e "\n${CYAN}📊 Changes to be pulled (branch: $CURRENT_BRANCH):${NC}"
git log HEAD..origin/$CURRENT_BRANCH --oneline --decorate | sed 's/^/  /'

# Confirm update
echo -e "\n${YELLOW}⚠️  Ready to update. Continue? (y/N): ${NC}"
read -r confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo -e "${RED}❌ Update cancelled by user${NC}"
    exit 0
fi

# Pull latest code
echo -e "\n${YELLOW}📥 Pulling latest code from Git...${NC}"
git pull origin "$CURRENT_BRANCH"
echo -e "${GREEN}✅ Code updated successfully${NC}"

# Activate virtual environment
echo -e "\n${YELLOW}🐍 Activating virtual environment...${NC}"
source .venv/bin/activate

# Update dependencies
echo -e "${YELLOW}📦 Updating Python dependencies...${NC}"
pip install -r requirements.txt --upgrade --quiet
echo -e "${GREEN}✅ Dependencies updated${NC}"

# Run database migrations (if using Alembic)
if [ -f "alembic.ini" ]; then
    echo -e "\n${YELLOW}🗄️  Running database migrations...${NC}"
    # alembic upgrade head
    # Uncomment above line when you set up Alembic migrations
    echo -e "ℹ️  Migration step skipped (not configured)"
fi

# Restart application
if [ "$RESTART_ENABLED" = true ]; then
    echo -e "\n${YELLOW}🔄 Restarting application...${NC}"
    
    # Check if systemd service exists
    if systemctl list-units --full -all | grep -Fq "$SERVICE_NAME.service"; then
        sudo systemctl restart "$SERVICE_NAME"
        echo -e "${GREEN}✅ Service '$SERVICE_NAME' restarted${NC}"
        sleep 2
        systemctl status "$SERVICE_NAME" --no-pager
    else
        echo -e "${YELLOW}ℹ️  No systemd service found. Checking for running processes...${NC}"
        
        # Kill existing uvicorn processes
        pkill -f "uvicorn app.main:app" || true
        
        echo -e "${YELLOW}💡 Please restart manually:${NC}"
        echo -e "   uvicorn app.main:app --host 0.0.0.0 --port 8010"
        echo -e "\n   Or run in background:"
        echo -e "   nohup uvicorn app.main:app --host 0.0.0.0 --port 8010 > app.log 2>&1 &"
    fi
fi

echo -e "\n${GREEN}"
echo "========================================"
echo "✅ Update completed successfully!"
echo "========================================"
echo -e "${NC}"

# Show application status
echo -e "${CYAN}📊 Application Status:${NC}"
echo -e "  Current Branch: $CURRENT_BRANCH"
echo -e "  Last Commit: $(git log -1 --pretty=format:'%h - %s (%cr)')"
echo -e "  Python Version: $(python --version)"
echo ""
