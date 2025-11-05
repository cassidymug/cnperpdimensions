#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Update CNPERP application from Git repository
.DESCRIPTION
    Pulls latest code, updates dependencies, and restarts the application
.EXAMPLE
    .\update_app.ps1
#>

param(
    [switch]$SkipBackup = $false,
    [switch]$SkipRestart = $false
)

$ErrorActionPreference = "Stop"
$AppRoot = Split-Path -Parent $PSScriptRoot

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "🔄 CNPERP Application Update Script" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

try {
    # Navigate to application root
    Set-Location $AppRoot
    Write-Host "📁 Working directory: $AppRoot" -ForegroundColor Yellow

    # Check if we're in a git repository
    if (-not (Test-Path ".git")) {
        Write-Host "❌ Error: Not a git repository!" -ForegroundColor Red
        Write-Host "Run: git init && git remote add origin https://github.com/cassidymug/cnperp-python.git" -ForegroundColor Yellow
        exit 1
    }

    # Backup database (unless skipped)
    if (-not $SkipBackup) {
        Write-Host "💾 Creating database backup..." -ForegroundColor Yellow
        & .\.venv\Scripts\python.exe -c "from app.services.backup_service import BackupService; from app.core.database import SessionLocal; db = SessionLocal(); BackupService(db).create_backup('pre_update'); db.close()"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "⚠️  Backup failed, but continuing..." -ForegroundColor Yellow
        } else {
            Write-Host "✅ Database backup completed" -ForegroundColor Green
        }
    }

    # Stash any local changes
    Write-Host "`n📦 Stashing local changes..." -ForegroundColor Yellow
    git stash push -m "Auto-stash before update $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

    # Fetch latest changes
    Write-Host "🌐 Fetching from remote..." -ForegroundColor Yellow
    git fetch origin

    # Show what will be updated
    $currentBranch = git branch --show-current
    Write-Host "`n📊 Changes to be pulled (branch: $currentBranch):" -ForegroundColor Cyan
    git log HEAD..origin/$currentBranch --oneline --decorate | ForEach-Object {
        Write-Host "  $_" -ForegroundColor Gray
    }

    # Confirm update
    Write-Host "`n⚠️  Ready to update. Continue? (Y/N): " -ForegroundColor Yellow -NoNewline
    $confirm = Read-Host
    if ($confirm -ne 'Y' -and $confirm -ne 'y') {
        Write-Host "❌ Update cancelled by user" -ForegroundColor Red
        exit 0
    }

    # Pull latest code
    Write-Host "`n📥 Pulling latest code from Git..." -ForegroundColor Yellow
    git pull origin $currentBranch
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Git pull failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Code updated successfully" -ForegroundColor Green

    # Activate virtual environment
    Write-Host "`n🐍 Activating virtual environment..." -ForegroundColor Yellow
    & .\.venv\Scripts\Activate.ps1

    # Update dependencies
    Write-Host "📦 Updating Python dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt --upgrade --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Dependency update failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Dependencies updated" -ForegroundColor Green

    # Run database migrations (if using Alembic)
    if (Test-Path "alembic.ini") {
        Write-Host "`n🗄️  Running database migrations..." -ForegroundColor Yellow
        # alembic upgrade head
        # Uncomment above line when you set up Alembic migrations
        Write-Host "ℹ️  Migration step skipped (not configured)" -ForegroundColor Gray
    }

    # Restart application
    if (-not $SkipRestart) {
        Write-Host "`n🔄 Restarting application..." -ForegroundColor Yellow
        
        # Method 1: If running as Windows Service
        $serviceName = "CNPERP"
        $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
        if ($service) {
            Restart-Service -Name $serviceName -Force
            Write-Host "✅ Service '$serviceName' restarted" -ForegroundColor Green
            Start-Sleep -Seconds 2
            Get-Service -Name $serviceName
        }
        # Method 2: If running manually, kill and restart
        else {
            Write-Host "ℹ️  No Windows Service found. Please restart manually:" -ForegroundColor Yellow
            Write-Host "   Stop current process (Ctrl+C in terminal)" -ForegroundColor Gray
            Write-Host "   Then run: uvicorn app.main:app --reload --host 0.0.0.0 --port 8010" -ForegroundColor Gray
        }
    }

    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host "✅ Update completed successfully!" -ForegroundColor Green
    Write-Host "========================================`n" -ForegroundColor Green

    # Show application status
    Write-Host "📊 Application Status:" -ForegroundColor Cyan
    Write-Host "  Current Branch: $currentBranch" -ForegroundColor Gray
    Write-Host "  Last Commit: $(git log -1 --pretty=format:'%h - %s (%cr)')" -ForegroundColor Gray
    Write-Host "  Python Version: $(& .\.venv\Scripts\python.exe --version)" -ForegroundColor Gray

} catch {
    Write-Host "`n❌ Update failed with error:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "`n💡 To rollback, run: git reset --hard HEAD@{1}" -ForegroundColor Yellow
    exit 1
}
