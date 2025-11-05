# CNPERP Local Network Installation Guide

This guide walks through installing and serving the CNPERP FastAPI application on a local server so that other devices on the same LAN or Wi-Fi network can access it. Detailed instructions are provided for Windows Server 2025 and Linux (Ubuntu 22.04 LTS).

> **Audience:** IT administrators or power users comfortable with command-line work.

> **Platforms Covered:** Windows Server 2025 (PowerShell 5.1+) and Ubuntu Server 22.04 LTS.
---

## 1. Windows Server 2025 Installation

### 1.1. Prepare Windows
1. Install all pending Windows Updates and reboot.
2. Assign a static IP (Settings → Network & internet → Ethernet → Edit IP assignment).
3. Install required dependencies using an elevated PowerShell session:

```powershell
winget install -e --id Git.Git
winget install -e --id Python.Python.3.11
winget install -e --id PostgreSQL.PostgreSQL.15
winget install -e --id OpenJS.NodeJS.LTS      # optional – frontend builds
winget install -e --id Microsoft.VisualStudio.2022.BuildTools  # optional – native deps
```

Record the PostgreSQL superuser password and confirm the port (default 5432).

### 1.2. Configure Windows Firewall

```powershell
New-NetFirewallRule -DisplayName "CNPERP Postgres" -Direction Inbound -Protocol TCP -LocalPort 5432 -Action Allow
New-NetFirewallRule -DisplayName "CNPERP API" -Direction Inbound -Protocol TCP -LocalPort 8010 -Action Allow
```

Add ports 80/443 if you plan to proxy via IIS/Nginx later.

### 1.3. PostgreSQL Database

```powershell
"C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -c "CREATE DATABASE cnperp_db;"
"C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -c "CREATE USER cnperp_user WITH PASSWORD 'StrongPassword!123';"
"C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE cnperp_db TO cnperp_user;"
```

Adjust the password and ensure `postgresql.conf` allows local connections (default).

### 1.4. Clone Repository

```powershell
cd C:\dev
git clone https://github.com/cassidymug/cnperp-python.git
cd cnperp-python
```

### 1.5. Python Virtual Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Install additional requirements (e.g., dev extras) as needed.

### 1.6. Configure `.env`

```powershell
Copy-Item .env.example .env
notepad .env
```

Set at minimum:

```
APP_ENV=production
DATABASE_URL=postgresql+psycopg2://cnperp_user:StrongPassword!123@localhost:5432/cnperp_db
SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(32))">
ALLOWED_HOSTS=0.0.0.0,localhost,<server-ip>
```

Add SMTP, object storage, or integration credentials as applicable.

### 1.7. Database Migrations & Seeds

```powershell
alembic upgrade head
```

Run any seed scripts under `scripts/` if desired.

### 1.8. Build Static Assets (Optional)

```powershell
npm install
npm run build
```

### 1.9. Start Application

**Development:**

```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --reload --host 0.0.0.0 --port 8010
```

**Production:**

```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8010 --workers 4
```

Optionally use Gunicorn (`pip install gunicorn`):

```powershell
.\.venv\Scripts\gunicorn.exe -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8010 --workers 4
```

### 1.10. Run as a Service (Optional)
Install [NSSM](https://nssm.cc/download) and configure:

```powershell
nssm install CNPERP "C:\dev\cnperp-python\.venv\Scripts\uvicorn.exe" app.main:app --host 0.0.0.0 --port 8010 --workers 4
nssm start CNPERP
```

### 1.11. Verify LAN Access

From another device:

```
http://<server-ip>:8010/docs
```

If unreachable, verify `ipconfig`, firewall, and that the process is listening (`netstat -ano | findstr 8010`).

### 1.12. IIS Reverse Proxy (Optional)

1. Install IIS, ARR, and URL Rewrite.
2. Create a site bound to port 80.
3. Add rewrite rule mapping `/(.*)` to `http://localhost:8010/{R:1}`.
4. Restart IIS.

### 1.13. Scheduled Backups

```powershell
"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe" -h localhost -U cnperp_user -F c -b -v -f "C:\backups\cnperp_%DATE:~10,4%-%DATE:~4,2%-%DATE:~7,2%.backup" cnperp_db
```

Schedule via Task Scheduler; store credentials in `%APPDATA%\postgresql\pgpass.conf`.

---

## 2. Linux Server Installation (Ubuntu 22.04 LTS)

### 2.1. System Preparation

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3.11 python3.11-venv python3-pip build-essential libpq-dev
```

### 2.2. PostgreSQL Setup

```bash
sudo apt install -y postgresql postgresql-contrib
```

Adjust `/etc/postgresql/14/main/postgresql.conf`:

```
listen_addresses = '*'
```

Allow LAN access in `/etc/postgresql/14/main/pg_hba.conf`:

```
host    all    all    192.168.0.0/16    md5
```

Restart PostgreSQL:

```bash
sudo systemctl restart postgresql
```

### 2.3. Create Database/User

```bash
sudo -u postgres psql <<'SQL'
CREATE DATABASE cnperp_db;
CREATE USER cnperp_user WITH PASSWORD 'StrongPassword!123';
GRANT ALL PRIVILEGES ON DATABASE cnperp_db TO cnperp_user;
ALTER USER cnperp_user SET search_path TO public;
SQL
```

### 2.4. Clone Repository

```bash
mkdir -p ~/cnperp && cd ~/cnperp
git clone https://github.com/cassidymug/cnperp-python.git
cd cnperp-python
```

### 2.5. Python Environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.6. Configure `.env`

```bash
cp .env.example .env
nano .env
```

Set values analogous to Windows (host `localhost`).

### 2.7. Migrations & Seeds

```bash
alembic upgrade head
```

Run optional seeds as needed.

### 2.8. Build Assets (Optional)

```bash
sudo apt install -y nodejs npm
npm install
npm run build
```

### 2.9. Launch with Uvicorn

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8010 --workers 4
```

### 2.10. Systemd Service
Create `/etc/systemd/system/cnperp.service`:

```ini
[Unit]
Description=CNPERP FastAPI Service
After=network.target postgresql.service

[Service]
User=cnperp
WorkingDirectory=/home/cnperp/cnperp-python
Environment="PATH=/home/cnperp/cnperp-python/.venv/bin"
ExecStart=/home/cnperp/cnperp-python/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8010 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable cnperp
sudo systemctl start cnperp
```

### 2.11. Nginx Reverse Proxy (Optional)

```bash
sudo apt install -y nginx
sudo tee /etc/nginx/sites-available/cnperp <<'NGINX'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX
sudo ln -s /etc/nginx/sites-available/cnperp /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx
```

### 2.12. HTTPS (Optional)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d cnperp.local
```

Use a valid domain or distribute the self-signed certificate to LAN clients.

### 2.13. Automated Backups
Create `/usr/local/bin/cnperp_backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/cnperp"
mkdir -p "$BACKUP_DIR"
sudo -u postgres pg_dump -Fc cnperp_db > "$BACKUP_DIR/cnperp_$(date +%F).dump"
find "$BACKUP_DIR" -type f -mtime +14 -delete
```

```bash
sudo chmod +x /usr/local/bin/cnperp_backup.sh
sudo crontab -e
0 2 * * * /usr/local/bin/cnperp_backup.sh
```

### 2.14. Monitoring
- View service logs: `journalctl -u cnperp -f`
- Install `htop`, `glances`, or integrate with Prometheus exporters.

---

## 3. Verification & LAN Tips

1. Reserve static IPs (router DHCP reservation or manual configuration).
2. Optionally create a local DNS entry (e.g., `cnperp.lan`).
3. From a client machine:
   - `ping <server-ip>`
   - `curl http://<server-ip>:8010/health`
   - Visit `http://<server-ip>:8010/docs`
4. Confirm OS and router firewalls allow the required ports.

---

## 4. Troubleshooting Checklist

| Issue | Possible Cause | Resolution |
|-------|----------------|------------|
| API unreachable | Firewall rules, wrong host bind | Ensure `--host 0.0.0.0`/reverse proxy configured, open ports |
| DB auth failures | Incorrect credentials or unreachable DB | Verify `.env` `DATABASE_URL`, ensure PostgreSQL running |
| Alembic errors | Migration mismatch | Use `alembic history`, resolve divergences |
| Static files missing | Frontend not built | Run `npm run build`; check static config |
| Slow throughput | Single worker | Increase Uvicorn workers or add Nginx caching |

---

Following these platform-specific instructions will get CNPERP running on either Windows Server 2025 or Ubuntu 22.04 and reachable across your local network. Adapt commands for other distributions or adjust ports and security policies as needed.
