# Quick Start: Git + VS Code Remote Setup

## 📋 Prerequisites Checklist

- [ ] Remote server (Linux or Windows Server)
- [ ] SSH access to remote server
- [ ] Git installed on remote server
- [ ] Python 3.10+ installed on remote server
- [ ] PostgreSQL installed on remote server
- [ ] VS Code installed on your local machine

---

## 🚀 Quick Setup (5 Steps)

### Step 1: Generate SSH Key (Local Machine)

**Windows PowerShell:**
```powershell
ssh-keygen -t ed25519 -C "your_email@example.com"
# Press Enter 3 times (use default location, no passphrase)
```

**Linux/Mac:**
```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
# Press Enter 3 times
```

### Step 2: Copy SSH Key to Server

**Replace `username` and `server-ip` with your details:**

```bash
# Windows
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh username@server-ip "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"

# Linux/Mac
ssh-copy-id username@server-ip
```

### Step 3: Configure VS Code Remote SSH

1. Install "Remote - SSH" extension in VS Code
2. Press `F1` → Type "Remote-SSH: Open SSH Configuration File"
3. Add this configuration:

```
Host cnperp-prod
    HostName your-server-ip
    User your-username
    Port 22
    IdentityFile ~/.ssh/id_ed25519
```

### Step 4: Deploy Application to Server

**Connect to server and run these commands:**

```bash
# Connect via SSH
ssh cnperp-prod

# Create app directory
mkdir -p ~/apps && cd ~/apps

# Clone repository
git clone https://github.com/cassidymug/cnperp-python.git
cd cnperp-python

# Setup Python environment
python3 -m venv .venv
source .venv/bin/activate  # Linux
# or .\.venv\Scripts\Activate.ps1  # Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
nano .env
```

**Add to .env file:**
```env
DATABASE_URL=postgresql://username:password@localhost:5432/cnperp_db
SECRET_KEY=your-secret-key-here
ENVIRONMENT=production
DEBUG=False
```

### Step 5: Connect VS Code to Server

1. Press `F1` in VS Code
2. Type: "Remote-SSH: Connect to Host"
3. Select "cnperp-prod"
4. Click "Open Folder" → Select `/home/username/apps/cnperp-python`

**✅ You're now connected! Edit code directly on the server.**

---

## 📦 Daily Update Workflow

### Option 1: Use Built-in Update Script (Easiest)

**In VS Code connected to remote server:**

1. Open Terminal (`Ctrl+\``)
2. Run:
   ```bash
   ./deploy/update_app.sh  # Linux
   # or
   .\deploy\update_app.ps1  # Windows
   ```

### Option 2: Use VS Code Tasks (Recommended)

1. Press `Ctrl+Shift+P`
2. Type: "Tasks: Run Task"
3. Select: "Deploy: Full Application Update"

### Option 3: Manual Git Pull

**In VS Code terminal:**
```bash
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart cnperp
```

---

## 🔧 Set Up Systemd Service (Linux)

**Run on server:**

```bash
sudo nano /etc/systemd/system/cnperp.service
```

**Paste this configuration (update paths):**
```ini
[Unit]
Description=CNPERP ERP Application
After=network.target postgresql.service

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/apps/cnperp-python
Environment="PATH=/home/your-username/apps/cnperp-python/.venv/bin"
ExecStart=/home/your-username/apps/cnperp-python/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8010
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable cnperp
sudo systemctl start cnperp
sudo systemctl status cnperp
```

---

## 🌐 Set Up Nginx (Optional but Recommended)

```bash
sudo apt install nginx -y
sudo nano /etc/nginx/sites-available/cnperp
```

**Add:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Enable:**
```bash
sudo ln -s /etc/nginx/sites-available/cnperp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 📊 Useful Commands

```bash
# View logs
sudo journalctl -u cnperp -f

# Restart application
sudo systemctl restart cnperp

# Check status
sudo systemctl status cnperp

# View recent logs
sudo journalctl -u cnperp -n 100

# Create backup
python -c "from app.services.backup_service import BackupService; from app.core.database import SessionLocal; db = SessionLocal(); BackupService(db).create_backup(); db.close()"
```

---

## 🆘 Troubleshooting

### Can't connect via SSH
```bash
# Test connection
ssh -v username@server-ip

# Check SSH service
sudo systemctl status sshd
```

### Application won't start
```bash
sudo systemctl status cnperp
sudo journalctl -u cnperp -n 50
```

### Port already in use
```bash
sudo lsof -i :8010
sudo kill -9 <PID>
```

### Permission denied
```bash
sudo chown -R your-username:your-username ~/apps/cnperp-python
chmod +x deploy/update_app.sh
```

---

## 📚 Next Steps

1. ✅ Set up SSL certificate (Certbot)
2. ✅ Configure automated backups
3. ✅ Set up monitoring
4. ✅ Review security settings

**For detailed instructions, see: `deploy/setup_remote_server.md`**

---

## 🎯 Summary

**You now have:**
- ✅ Git-based deployment
- ✅ VS Code Remote SSH access
- ✅ One-command updates via scripts
- ✅ Automated service management
- ✅ Easy log viewing

**To update application:**
1. Edit code in VS Code (connected to remote)
2. Commit and push to Git
3. On server: Run `./deploy/update_app.sh`
4. Application automatically restarts

**Or connect VS Code and pull changes directly on the server!**
