# Quick LAN Installation - Windows Server

## 🎯 Goal
Install CNPERP on your Windows server so all computers on your network can access it.

---

## ⚡ Super Quick Install (Copy & Paste)

### Step 1: Connect to Your Server

**Option A: Remote Desktop**
1. Press `Win+R` → Type `mstsc` → Enter
2. Enter server IP (e.g., `192.168.1.100`)
3. Login with admin credentials

**Option B: PowerShell Remote**
```powershell
# From your PC
Enter-PSSession -ComputerName 192.168.1.100 -Credential (Get-Credential)
```

---

### Step 2: Install Required Software (One Command)

**Run this in PowerShell as Administrator:**

```powershell
# Install everything needed
winget install -e --id Git.Git
winget install -e --id Python.Python.3.11
winget install -e --id PostgreSQL.PostgreSQL.15

# Restart PowerShell after installation
```

---

### Step 3: Configure PostgreSQL Database

```powershell
# Navigate to PostgreSQL bin
cd "C:\Program Files\PostgreSQL\15\bin"

# Create database and user
.\psql.exe -U postgres -c "CREATE DATABASE cnperp_db;"
.\psql.exe -U postgres -c "CREATE USER cnperp_user WITH PASSWORD 'CNP3rp@2025';"
.\psql.exe -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE cnperp_db TO cnperp_user;"
```

**Note**: When prompted, enter the PostgreSQL password you set during installation.

---

### Step 4: Clone Your Repository

```powershell
# Create app directory
cd C:\
mkdir apps
cd apps

# Clone from GitHub
git clone https://github.com/cassidymug/cnperpdimensions.git
cd cnperpdimensions
```

---

### Step 5: Setup Python Environment

```powershell
# Create virtual environment
python -m venv .venv

# Activate it
.\.venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

---

### Step 6: Configure Database Connection

```powershell
# Create environment file
notepad .env
```

**Paste this into .env file:**

```env
# Database Configuration
DATABASE_URL=postgresql://cnperp_user:CNP3rp@2025@localhost:5432/cnperp_db

# Security
SECRET_KEY=your-secret-key-change-this-in-production
ENVIRONMENT=production

# Server Configuration
ALLOWED_HOSTS=0.0.0.0,localhost,192.168.1.100
DEBUG=False

# CORS (Allow all network devices)
CORS_ORIGINS=*
```

**Save and close Notepad**

---

### Step 7: Run Database Migrations

```powershell
# Still in the app directory with .venv activated
alembic upgrade head
```

---

### Step 8: Open Firewall Ports

```powershell
# Allow port 8010 (API)
New-NetFirewallRule -DisplayName "CNPERP API" -Direction Inbound -Protocol TCP -LocalPort 8010 -Action Allow

# Allow PostgreSQL (optional, if other servers need DB access)
New-NetFirewallRule -DisplayName "CNPERP Database" -Direction Inbound -Protocol TCP -LocalPort 5432 -Action Allow
```

---

### Step 9: Start the Application

**For Testing (with auto-reload):**
```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --reload --host 0.0.0.0 --port 8010
```

**For Production (4 workers, faster):**
```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8010 --workers 4
```

---

### Step 10: Test from Another Computer

**On any computer in your network:**

1. Open browser
2. Go to: `http://192.168.1.100:8010/static/login.html`
3. Login with default credentials:
   - Username: `admin`
   - Password: `adminpassword`

**API Documentation:** `http://192.168.1.100:8010/docs`

---

## 🔧 Install as Windows Service (Optional but Recommended)

This keeps the app running even after you log out.

### Option 1: Using NSSM (Easiest)

```powershell
# Download NSSM
Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile "nssm.zip"
Expand-Archive -Path "nssm.zip" -DestinationPath "C:\nssm"

# Install as service
C:\nssm\nssm-2.24\win64\nssm.exe install CNPERP "C:\apps\cnperpdimensions\.venv\Scripts\uvicorn.exe"
C:\nssm\nssm-2.24\win64\nssm.exe set CNPERP AppParameters "app.main:app --host 0.0.0.0 --port 8010 --workers 4"
C:\nssm\nssm-2.24\win64\nssm.exe set CNPERP AppDirectory "C:\apps\cnperpdimensions"

# Start service
C:\nssm\nssm-2.24\win64\nssm.exe start CNPERP

# Check status
Get-Service CNPERP
```

### Option 2: Using Built-in Task Scheduler

1. Open Task Scheduler
2. Create Task → Name: "CNPERP ERP"
3. Trigger: At startup
4. Action: Start program
   - Program: `C:\apps\cnperpdimensions\.venv\Scripts\uvicorn.exe`
   - Arguments: `app.main:app --host 0.0.0.0 --port 8010 --workers 4`
   - Start in: `C:\apps\cnperpdimensions`
5. Settings: Run whether user is logged on or not

---

## 🔄 Update Application (Future Updates)

**To update after you push changes to GitHub:**

```powershell
cd C:\apps\cnperpdimensions

# Pull latest code
git pull origin main

# Update dependencies
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt --upgrade

# Restart service
Restart-Service CNPERP
# or if running manually, stop (Ctrl+C) and restart
```

**Or use the automated script:**
```powershell
.\deploy\update_app.ps1
```

---

## 📊 Server Information

**Find your server's IP address:**
```powershell
ipconfig | findstr IPv4
```

**Check if app is running:**
```powershell
Get-Process | Where-Object {$_.ProcessName -like "*uvicorn*" -or $_.ProcessName -like "*python*"}
```

**Check what's listening on port 8010:**
```powershell
netstat -ano | findstr 8010
```

**View logs:**
```powershell
Get-Content C:\apps\cnperpdimensions\logs\app.log -Tail 50 -Wait
```

---

## 🆘 Troubleshooting

### Can't access from other computers

1. **Check Windows Firewall:**
   ```powershell
   Get-NetFirewallRule -DisplayName "CNPERP*"
   ```

2. **Verify app is listening on all interfaces:**
   ```powershell
   netstat -ano | findstr 8010
   ```
   Should show `0.0.0.0:8010` not `127.0.0.1:8010`

3. **Test from server itself first:**
   ```
   http://localhost:8010/docs
   ```

4. **Ping server from another computer:**
   ```
   ping 192.168.1.100
   ```

### Database connection errors

```powershell
# Test PostgreSQL connection
cd "C:\Program Files\PostgreSQL\15\bin"
.\psql.exe -U cnperp_user -d cnperp_db -h localhost
# Enter password: CNP3rp@2025
```

### Python/Uvicorn not found

```powershell
# Ensure virtual environment is activated
.\.venv\Scripts\Activate.ps1

# Check Python path
(Get-Command python).Source
# Should show: C:\apps\cnperpdimensions\.venv\Scripts\python.exe
```

---

## ✅ Success Checklist

- [ ] PostgreSQL installed and database created
- [ ] Python virtual environment created
- [ ] Dependencies installed
- [ ] .env file configured
- [ ] Database migrations run
- [ ] Firewall ports opened (8010)
- [ ] Application starts without errors
- [ ] Can access from server browser (localhost:8010)
- [ ] Can access from another computer (server-ip:8010)
- [ ] Installed as Windows Service (optional)

---

## 📞 Default Access Information

**Application URL:** `http://<your-server-ip>:8010`
**Login Page:** `http://<your-server-ip>:8010/static/login.html`
**API Docs:** `http://<your-server-ip>:8010/docs`

**Default Credentials:**
- Username: `admin`
- Password: `adminpassword`

**⚠️ Change default password after first login!**

---

**Installation Time:** ~30 minutes
**Future Updates:** ~2 minutes with automated script

