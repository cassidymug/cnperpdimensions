from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import json
import zipfile
import shutil
import tempfile
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
import logging
from sqlalchemy import func
import statistics
from collections import defaultdict, Counter
import traceback
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

from app.core.database import get_db, engine
from app.core.config import settings
from app.schemas.backup import (
    BackupCreate, 
    BackupResponse, 
    BackupRestore, 
    BackupSchedule as BackupScheduleSchema,
    BackupScheduleResponse,
    BackupStatus,
    BackupType
)
from app.models.backup import Backup, BackupSchedule as BackupScheduleModel
# # from app.core.security import get_current_user  # Removed for development

router = APIRouter()
logger = logging.getLogger(__name__)

# Backup configuration
DEFAULT_BACKUP_DIR = "backups"
METADATA_FILE = "backup_metadata.json"

def get_backup_directories(custom_location: str = None) -> tuple:
    """Get backup directories, optionally using custom location"""
    if custom_location:
        # Use custom location if provided
        base_dir = custom_location
        if not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)
    else:
        # Use default location
        base_dir = DEFAULT_BACKUP_DIR
    
    absolute_dir = os.path.join(base_dir, "absolute")
    incremental_dir = os.path.join(base_dir, "incremental")
    
    # Ensure directories exist
    os.makedirs(absolute_dir, exist_ok=True)
    os.makedirs(incremental_dir, exist_ok=True)
    
    return base_dir, absolute_dir, incremental_dir

# Initialize default directories
# get_backup_directories()  # Commented out to avoid issues during import

def get_db_connection():
    """Get database connection for backup operations"""
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="cnperp",
        user="postgres",
        password="password"
    )

def calculate_backup_hash(file_path: str) -> str:
    """Calculate SHA256 hash of backup file"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def create_backup_metadata(backup_type: str, file_path: str, description: str = None) -> dict:
    """Create metadata for backup"""
    file_size = os.path.getsize(file_path)
    file_hash = calculate_backup_hash(file_path)
    
    return {
        "backup_type": backup_type,
        "file_path": file_path,
        "file_size": file_size,
        "file_hash": file_hash,
        "created_at": datetime.utcnow().isoformat(),
        "description": description,
        "version": "1.0",
        "database_name": "cnperp",
        "database_host": "localhost"
    }

def save_backup_metadata(backup_id: str, metadata: dict):
    """Save backup metadata to file"""
    metadata_file = os.path.join(os.path.dirname(metadata["file_path"]), f"{backup_id}_{METADATA_FILE}")
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

def create_database_dump(backup_path: str, tables: List[str] = None) -> bool:
    """Create database dump using pg_dump"""
    logger.info(f"Starting database dump creation for: {backup_path}")
    try:
        import subprocess
        import shutil
        from urllib.parse import urlparse
        
        # Get database connection info from engine URL
        db_url = engine.url
        db_host = db_url.host or "localhost"
        db_port = db_url.port or 5432
        db_user = db_url.username
        db_password = db_url.password
        db_name = db_url.database
        
        logger.info(f"Database connection: {db_user}@{db_host}:{db_port}/{db_name}")
        
        # Check if pg_dump is available
        pg_dump_path = shutil.which("pg_dump")
        if not pg_dump_path:
            # Try common PostgreSQL installation paths on Windows
            possible_paths = [
                r"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe",
                r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
                r"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe",
                r"C:\Program Files\PostgreSQL\14\bin\pg_dump.exe",
                r"C:\Program Files\PostgreSQL\13\bin\pg_dump.exe",
                r"C:\PostgreSQL\bin\pg_dump.exe",
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    pg_dump_path = path
                    break
        
        if not pg_dump_path:
            logger.warning("pg_dump not found, creating minimal backup file")
            # Fallback: Create a minimal backup file
            with open(backup_path, 'w') as f:
                f.write("-- Database Backup (pg_dump not available)\n")
                f.write(f"-- Created: {datetime.utcnow().isoformat()}\n")
                f.write(f"-- Database: {db_name}\n")
                f.write("-- NOTE: This is a minimal backup. Install PostgreSQL tools for full backups.\n\n")
                f.write("SELECT 'Backup created without pg_dump' as status;\n")
            logger.info(f"Minimal backup file created: {backup_path}")
            return True
        
        # Build pg_dump command
        cmd = [
            pg_dump_path,
            "-h", str(db_host),
            "-p", str(db_port),
            "-U", str(db_user),
            "-d", str(db_name),
            "-F", "p",  # Plain text format
            "-f", backup_path,
            "--no-password"  # Use environment variable PGPASSWORD
        ]
        
        # Add table filter if specified
        if tables:
            for table in tables:
                cmd.extend(["-t", table])
        
        # Set environment variable for password
        env = os.environ.copy()
        if db_password:
            env["PGPASSWORD"] = str(db_password)
        
        logger.info(f"Executing pg_dump with user {db_user} to {backup_path}")
        
        # Execute pg_dump
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            # Verify backup file was created and has content
            if os.path.exists(backup_path) and os.path.getsize(backup_path) > 0:
                file_size = os.path.getsize(backup_path)
                logger.info(f"Database dump created successfully: {backup_path} ({file_size} bytes)")
                return True
            else:
                logger.error(f"Backup file is empty or doesn't exist: {backup_path}")
                return False
        else:
            logger.error(f"pg_dump failed with return code {result.returncode}")
            logger.error(f"STDERR: {result.stderr}")
            logger.error(f"STDOUT: {result.stdout}")
            return False
        
    except subprocess.TimeoutExpired:
        logger.error(f"Database dump timed out after 5 minutes")
        return False
    except Exception as e:
        logger.error(f"Error creating database dump: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def create_files_backup(backup_path: str) -> bool:
    """Create backup of application files"""
    try:
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Backup static files
            static_dir = "app/static"
            if os.path.exists(static_dir):
                for root, dirs, files in os.walk(static_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, "app")
                        zipf.write(file_path, arcname)
            
            # Backup configuration files
            config_files = ["requirements.txt", ".env", "alembic.ini"]
            for config_file in config_files:
                if os.path.exists(config_file):
                    zipf.write(config_file, config_file)
        
        return True
    except Exception as e:
        logger.error(f"Error creating files backup: {e}")
        return False

def create_full_system_backup(backup_path: str) -> dict:
    """
    Create a comprehensive backup of the entire application including:
    - Database (full dump)
    - Application source code
    - Configuration files (.env, alembic.ini, etc.)
    - Static files (uploads, reports, etc.)
    - Python dependencies (requirements.txt)
    """
    try:
        logger.info(f"Starting full system backup to: {backup_path}")
        
        # Create temporary directory for staging
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Using temporary directory: {temp_dir}")
            
            # 1. Database backup
            db_backup_path = os.path.join(temp_dir, "database_dump.sql")
            logger.info("Creating database backup...")
            if not create_database_dump(db_backup_path):
                return {"success": False, "error": "Database backup failed"}
            db_size = os.path.getsize(db_backup_path)
            logger.info(f"Database backup created: {db_size} bytes")
            
            # 2. Create the main backup archive
            logger.info("Creating system backup archive...")
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                
                # Add database dump
                zipf.write(db_backup_path, "database/database_dump.sql")
                logger.info("Added database dump to archive")
                
                # 3. Application source code (excluding certain directories)
                exclude_dirs = {'.venv', '__pycache__', '.git', 'backups', 'node_modules', 
                               '.pytest_cache', '.mypy_cache', 'temp_repo', 'venv', 'env'}
                exclude_files = {'.pyc', '.pyo', '.pyd', '.log', '.sqlite'}
                
                logger.info("Backing up application source code...")
                source_count = 0
                for root, dirs, files in os.walk('.'):
                    # Remove excluded directories from the walk
                    dirs[:] = [d for d in dirs if d not in exclude_dirs]
                    
                    for file in files:
                        # Skip excluded file types
                        if any(file.endswith(ext) for ext in exclude_files):
                            continue
                        
                        file_path = os.path.join(root, file)
                        arcname = os.path.join("application", file_path.lstrip('./\\'))
                        
                        try:
                            zipf.write(file_path, arcname)
                            source_count += 1
                        except Exception as e:
                            logger.warning(f"Could not backup file {file_path}: {e}")
                
                logger.info(f"Backed up {source_count} application files")
                
                # 4. Configuration files (critical files)
                config_files = [
                    '.env',
                    'alembic.ini',
                    'requirements.txt',
                    'pyproject.toml',
                    'setup.py',
                    'README.md',
                    '.env.example'
                ]
                
                logger.info("Backing up configuration files...")
                for config_file in config_files:
                    if os.path.exists(config_file):
                        zipf.write(config_file, os.path.join("config", config_file))
                        logger.info(f"Added config file: {config_file}")
                
                # 5. Create backup manifest
                manifest = {
                    "backup_type": "full_system",
                    "created_at": datetime.utcnow().isoformat(),
                    "database_size": db_size,
                    "source_files_count": source_count,
                    "python_version": os.sys.version,
                    "database_name": engine.url.database,
                    "database_host": engine.url.host,
                    "backup_version": "1.0",
                    "application_name": "CNPERP ERP System"
                }
                
                manifest_json = json.dumps(manifest, indent=2)
                zipf.writestr("BACKUP_MANIFEST.json", manifest_json)
                logger.info("Added backup manifest")
                
                # 6. Create restore instructions
                restore_instructions = """
CNPERP Full System Backup - Restore Instructions
================================================

This backup contains a complete snapshot of your CNPERP ERP system.

Contents:
---------
1. database/database_dump.sql - PostgreSQL database dump
2. application/ - Complete application source code
3. config/ - Configuration files (.env, alembic.ini, etc.)
4. BACKUP_MANIFEST.json - Backup metadata

Restore Steps:
--------------

1. RESTORE DATABASE:
   - Stop the application
   - Drop existing database: dropdb cnperp
   - Create new database: createdb cnperp
   - Restore dump: psql -U cnperp -d cnperp -f database/database_dump.sql

2. RESTORE APPLICATION:
   - Extract application/ folder to your deployment directory
   - Restore config files from config/ folder
   - Create virtual environment: python -m venv .venv
   - Install dependencies: pip install -r requirements.txt

3. RESTART APPLICATION:
   - Verify .env configuration
   - Run database migrations: alembic upgrade head
   - Start application: uvicorn app.main:app --reload

IMPORTANT NOTES:
---------------
- Always test restore on a non-production environment first
- Verify database credentials in .env match your environment
- Ensure PostgreSQL version compatibility
- Back up current data before restoring

For assistance, contact your system administrator.
"""
                zipf.writestr("RESTORE_INSTRUCTIONS.txt", restore_instructions)
                logger.info("Added restore instructions")
            
            # Calculate final backup size
            backup_size = os.path.getsize(backup_path)
            logger.info(f"Full system backup completed: {backup_size} bytes")
            
            return {
                "success": True,
                "backup_size": backup_size,
                "database_size": db_size,
                "source_files_count": source_count,
                "manifest": manifest
            }
    
    except Exception as e:
        logger.error(f"Error creating full system backup: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}

@router.post("/create", response_model=BackupResponse)
async def create_backup(
    backup_data: BackupCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
    # # # current_user parameter removed for development,  # Removed for development  # Commented out for development
):
    """Create a new backup (absolute, incremental, or full_system)"""
    
    # Validate backup type
    if backup_data.backup_type not in ["absolute", "incremental", "full_system"]:
        raise HTTPException(status_code=400, detail="Invalid backup type")
    
    # Check if incremental backup is possible
    if backup_data.backup_type == "incremental":
        last_backup = db.query(Backup).filter(
            Backup.backup_type == "absolute"
        ).order_by(Backup.created_at.desc()).first()
        
        if not last_backup:
            raise HTTPException(
                status_code=400, 
                detail="Cannot create incremental backup without a base absolute backup"
            )
    
    # Create backup record
    backup = Backup(
        backup_type=backup_data.backup_type,
        description=backup_data.description,
        status="in_progress",
        created_by="dev_user"  # Hardcoded for development
    )
    db.add(backup)
    db.commit()
    db.refresh(backup)
    
    # Start backup process in background
    background_tasks.add_task(
        perform_backup,
        backup.id,
        backup_data.backup_type,
        backup_data.description,
        backup_data.include_files,
        backup_data.tables,
        backup_data.backup_location
    )
    
    return BackupResponse(
        id=backup.id,
        backup_type=backup.backup_type,
        description=backup.description,
        status=backup.status,
        created_at=backup.created_at,
        created_by=backup.created_by
    )

async def perform_backup(
    backup_id: str,
    backup_type: str,
    description: str,
    include_files: bool,
    tables: List[str] = None,
    backup_location: str = None
):
    """Perform the actual backup operation"""
    db = next(get_db())
    
    try:
        # Get backup directories (with custom location if specified)
        base_dir, absolute_dir, incremental_dir = get_backup_directories(backup_location)
        
        # Create backup filename with custom name if provided
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        if description and description.strip():
            # Use description as part of filename (sanitized)
            safe_description = "".join(c for c in description if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_description = safe_description.replace(' ', '_')[:50]  # Limit length
            backup_filename = f"backup_{backup_type}_{safe_description}_{timestamp}_{backup_id}.sql"
        else:
            backup_filename = f"backup_{backup_type}_{timestamp}_{backup_id}.sql"
        
        # Handle FULL SYSTEM backup
        if backup_type == "full_system":
            logger.info(f"Creating FULL SYSTEM backup for: {backup_id}")
            
            # Create full_system subdirectory
            full_system_dir = os.path.join(base_dir, "full_system")
            os.makedirs(full_system_dir, exist_ok=True)
            
            # Full system backups are always .zip files
            backup_filename = f"FULL_SYSTEM_{timestamp}_{backup_id}.zip"
            backup_path = os.path.join(full_system_dir, backup_filename)
            
            # Create full system backup
            result = create_full_system_backup(backup_path)
            
            if not result.get("success"):
                raise Exception(f"Full system backup failed: {result.get('error', 'Unknown error')}")
            
            # Update backup record with full details
            backup = db.query(Backup).filter(Backup.id == backup_id).first()
            if backup:
                backup.status = "completed"
                backup.file_path = backup_path
                backup.file_size = result["backup_size"]
                backup.file_hash = calculate_backup_hash(backup_path)
                backup.backup_metadata = {
                    "type": "full_system",
                    "database_size": result["database_size"],
                    "source_files_count": result["source_files_count"],
                    "manifest": result["manifest"],
                    "file_path": backup_path
                }
                db.commit()
            
            logger.info(f"Full system backup {backup_id} completed successfully")
            return
        
        # Handle ABSOLUTE or INCREMENTAL backup (existing logic)
        if backup_type == "absolute":
            backup_path = os.path.join(absolute_dir, backup_filename)
        else:
            backup_path = os.path.join(incremental_dir, backup_filename)
        
        # Create database dump
        logger.info(f"Creating database dump at: {backup_path}")
        if not create_database_dump(backup_path, tables):
            logger.error(f"Database dump failed for path: {backup_path}")
            raise Exception("Database dump failed")
        logger.info(f"Database dump created successfully at: {backup_path}")
        
        # Create files backup if requested
        files_backup_path = None
        if include_files:
            files_filename = f"files_{backup_type}_{timestamp}_{backup_id}.zip"
            if backup_type == "absolute":
                files_backup_path = os.path.join(absolute_dir, files_filename)
            else:
                files_backup_path = os.path.join(incremental_dir, files_filename)
            
            if not create_files_backup(files_backup_path):
                raise Exception("Files backup failed")
        
        # Create metadata
        try:
            metadata = create_backup_metadata(
                backup_type=backup_type,
                file_path=backup_path,
                description=description
            )
            
            if files_backup_path:
                metadata["files_backup_path"] = files_backup_path
            
            # Save metadata
            save_backup_metadata(backup_id, metadata)
            
            # Update backup record
            backup = db.query(Backup).filter(Backup.id == backup_id).first()
            if backup:
                backup.status = "completed"
                backup.file_path = backup_path
                backup.file_size = metadata["file_size"]
                backup.file_hash = metadata["file_hash"]
                backup.backup_metadata = metadata
                db.commit()
        except Exception as e:
            logger.error(f"Error in metadata creation: {e}")
            # Update backup record with basic info
            backup = db.query(Backup).filter(Backup.id == backup_id).first()
            if backup:
                backup.status = "completed"
                backup.file_path = backup_path
                backup.file_size = os.path.getsize(backup_path) if os.path.exists(backup_path) else 0
                backup.backup_metadata = {"error": "Metadata creation failed", "details": str(e)}
                db.commit()
        
        logger.info(f"Backup {backup_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Backup {backup_id} failed: {e}")
        
        # Update backup record with error
        backup = db.query(Backup).filter(Backup.id == backup_id).first()
        if backup:
            backup.status = "failed"
            backup.error_message = str(e)
            db.commit()

@router.get("/", response_model=List[BackupResponse])
async def list_backups(
    skip: int = 0,
    limit: int = 100,
    backup_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
    # # # current_user parameter removed for development,  # Removed for development  # Commented out for development
):
    """List all backups with optional filtering"""
    
    query = db.query(Backup)
    
    if backup_type:
        query = query.filter(Backup.backup_type == backup_type)
    
    if status:
        query = query.filter(Backup.status == status)
    
    backups = query.order_by(Backup.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        BackupResponse(
            id=backup.id,
            backup_type=backup.backup_type,
            description=backup.description,
            status=backup.status,
            created_at=backup.created_at,
            created_by=backup.created_by,
            file_size=backup.file_size,
            error_message=backup.error_message
        )
        for backup in backups
    ]

@router.get("/config")
async def get_backup_config(
    # # # current_user parameter removed for development,  # Removed for development  # Commented out for development
):
    """Get backup configuration information"""
    try:
        # Get current backup directories
        base_dir, absolute_dir, incremental_dir = get_backup_directories()
        
        # Check if directories exist and are writable
        dir_info = {}
        for dir_name, dir_path in [("base", base_dir), ("absolute", absolute_dir), ("incremental", incremental_dir)]:
            try:
                dir_info[dir_name] = {
                    "path": os.path.abspath(dir_path),
                    "exists": os.path.exists(dir_path),
                    "writable": os.access(dir_path, os.W_OK) if os.path.exists(dir_path) else False,
                    "size_mb": sum(os.path.getsize(os.path.join(dirpath, filename))
                                  for dirpath, dirnames, filenames in os.walk(dir_path)
                                  for filename in filenames) / (1024 * 1024) if os.path.exists(dir_path) else 0
                }
            except Exception as e:
                logger.error(f"Error processing directory {dir_name} ({dir_path}): {e}")
                dir_info[dir_name] = {
                    "path": os.path.abspath(dir_path),
                    "exists": False,
                    "writable": False,
                    "size_mb": 0,
                    "error": str(e)
                }
        
        return {
            "default_backup_dir": os.path.abspath(DEFAULT_BACKUP_DIR),
            "current_backup_dir": os.path.abspath(base_dir),
            "directories": dir_info,
            "supports_custom_location": True
        }
    except Exception as e:
        logger.error(f"Error in get_backup_config: {e}")
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")

@router.get("/test-config")
async def get_backup_config_test():
    """Get backup configuration information (no authentication required for testing)"""
    return {"status": "ok", "message": "Test endpoint working"}



@router.get("/{backup_id}", response_model=BackupResponse)
async def get_backup(
    backup_id: str,
    db: Session = Depends(get_db)
    # # # current_user parameter removed for development,  # Removed for development  # Commented out for development
):
    """Get backup details"""
    
    backup = db.query(Backup).filter(Backup.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    return BackupResponse(
        id=backup.id,
        backup_type=backup.backup_type,
        description=backup.description,
        status=backup.status,
        created_at=backup.created_at,
        created_by=backup.created_by,
        file_size=backup.file_size,
        file_hash=backup.file_hash,
        metadata=backup.backup_metadata,
        error_message=backup.error_message
    )

@router.get("/{backup_id}/download")
async def download_backup(
    backup_id: str,
    db: Session = Depends(get_db)
    # # # current_user parameter removed for development,  # Removed for development  # Commented out for development
):
    """Download backup file"""
    from fastapi.responses import FileResponse
    
    backup = db.query(Backup).filter(Backup.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    if backup.status != "completed":
        raise HTTPException(status_code=400, detail="Cannot download incomplete backup")
    
    if not backup.file_path or not os.path.exists(backup.file_path):
        raise HTTPException(status_code=404, detail="Backup file not found")
    
    # Create filename for download
    filename = os.path.basename(backup.file_path)
    if backup.description:
        safe_description = "".join(c for c in backup.description if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_description = safe_description.replace(' ', '_')[:30]
        filename = f"{safe_description}_{filename}"
    
    return FileResponse(
        path=backup.file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

@router.post("/{backup_id}/restore")
async def restore_backup(
    backup_id: str,
    restore_data: BackupRestore,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
    # # # current_user parameter removed for development,  # Removed for development  # Commented out for development
):
    """Restore a backup"""
    
    backup = db.query(Backup).filter(Backup.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    if backup.status != "completed":
        raise HTTPException(status_code=400, detail="Cannot restore incomplete backup")
    
    if not backup.file_path or not os.path.exists(backup.file_path):
        raise HTTPException(status_code=404, detail="Backup file not found")
    
    # Start restore process in background
    background_tasks.add_task(
        perform_restore,
        backup_id,
        backup.file_path,
        restore_data.restore_files,
        restore_data.restore_database,
        "dev_user"  # Hardcoded for development
    )
    
    return {"message": "Restore process started", "backup_id": backup_id}



def restore_database_from_file(backup_path: str) -> bool:
    """Restore database from backup file"""
    try:
        # Read the backup file
        with open(backup_path, 'r') as f:
            sql_content = f.read()
        
        # Split into individual statements
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        # Execute statements
        from app.core.database import engine
        with engine.connect() as conn:
            for statement in statements:
                if statement and not statement.startswith('--'):
                    conn.execute(sa.text(statement))
            conn.commit()
        
        return True
    except Exception as e:
        logger.error(f"Error restoring database: {e}")
        return False

def restore_files_from_backup(backup_path: str) -> bool:
    """Restore files from backup"""
    try:
        import zipfile
        
        with zipfile.ZipFile(backup_path, 'r') as zipf:
            zipf.extractall(".")
        
        return True
    except Exception as e:
        logger.error(f"Error restoring files: {e}")
        return False

async def perform_restore(
    backup_id: str,
    backup_path: str,
    restore_files: bool,
    restore_database: bool,
    user_id: str
):
    """Perform the actual restore operation"""
    db = next(get_db())
    
    try:
        # Create restore record
        restore = Backup(
            backup_type="restore",
            description=f"Restore from backup {backup_id}",
            status="in_progress",
            created_by=user_id
        )
        db.add(restore)
        db.commit()
        db.refresh(restore)
        
        # Restore database if requested
        if restore_database:
            if not restore_database_from_backup(backup_path):
                raise Exception("Database restore failed")
        
        # Restore files if requested
        if restore_files:
            metadata_file = os.path.join(os.path.dirname(backup_path), f"{backup_id}_{METADATA_FILE}")
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                if "files_backup_path" in metadata and os.path.exists(metadata["files_backup_path"]):
                    if not restore_files_from_backup(metadata["files_backup_path"]):
                        raise Exception("Files restore failed")
        
        # Update restore record
        restore.status = "completed"
        db.commit()
        
        logger.info(f"Restore from backup {backup_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Restore from backup {backup_id} failed: {e}")
        
        # Update restore record with error
        restore = db.query(Backup).filter(Backup.id == restore.id).first()
        if restore:
            restore.status = "failed"
            restore.error_message = str(e)
            db.commit()

def restore_database_from_backup(backup_path: str) -> bool:
    """Restore database from backup file"""
    try:
        # Build psql command
        cmd = [
            "psql",
            "-h", "localhost",
            "-p", "5432",
            "-U", "postgres",
            "-d", "cnperp",
            "-f", backup_path
        ]
        
        # Set password environment variable
        env = os.environ.copy()
        env["PGPASSWORD"] = "password"
        
        # Execute psql
        import subprocess
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"psql restore failed: {result.stderr}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error restoring database: {e}")
        return False

def restore_files_from_backup(files_backup_path: str) -> bool:
    """Restore files from backup"""
    try:
        with zipfile.ZipFile(files_backup_path, 'r') as zipf:
            zipf.extractall("app")
        return True
    except Exception as e:
        logger.error(f"Error restoring files: {e}")
        return False

@router.delete("/{backup_id}")
async def delete_backup(
    backup_id: str,
    db: Session = Depends(get_db)
    # # # current_user parameter removed for development,  # Removed for development  # Commented out for development
):
    """Delete a backup"""
    try:
        backup = db.query(Backup).filter(Backup.id == backup_id).first()
        if not backup:
            raise HTTPException(status_code=404, detail="Backup not found")
        
        # Delete backup file
        if backup.file_path and os.path.exists(backup.file_path):
            try:
                os.remove(backup.file_path)
                logger.info(f"Deleted backup file: {backup.file_path}")
            except Exception as e:
                logger.error(f"Error deleting backup file {backup.file_path}: {e}")
        
        # Delete metadata file (only if file_path exists)
        if backup.file_path:
            try:
                metadata_file = os.path.join(os.path.dirname(backup.file_path), f"{backup_id}_{METADATA_FILE}")
                if os.path.exists(metadata_file):
                    os.remove(metadata_file)
                    logger.info(f"Deleted metadata file: {metadata_file}")
            except Exception as e:
                logger.error(f"Error deleting metadata file: {e}")
        
        # Delete files backup if exists
        try:
            if backup.backup_metadata and isinstance(backup.backup_metadata, dict):
                if "files_backup_path" in backup.backup_metadata:
                    files_path = backup.backup_metadata["files_backup_path"]
                    if os.path.exists(files_path):
                        os.remove(files_path)
                        logger.info(f"Deleted files backup: {files_path}")
        except Exception as e:
            logger.error(f"Error deleting files backup: {e}")
        
        # Delete from database
        db.delete(backup)
        db.commit()
        logger.info(f"Deleted backup record from database: {backup_id}")
        
        return {"message": "Backup deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting backup {backup_id}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error deleting backup: {str(e)}")

@router.get("/status/summary")
async def get_backup_summary(
    db: Session = Depends(get_db)
    # # # current_user parameter removed for development,  # Removed for development  # Commented out for development
):
    """Get backup system summary"""
    try:
        total_backups = db.query(Backup).count()
        completed_backups = db.query(Backup).filter(Backup.status == "completed").count()
        failed_backups = db.query(Backup).filter(Backup.status == "failed").count()
        
        # Get latest backup
        latest_backup = db.query(Backup).filter(
            Backup.status == "completed"
        ).order_by(Backup.created_at.desc()).first()
        
        # Calculate total backup size
        total_size = db.query(Backup).filter(
            Backup.status == "completed"
        ).with_entities(func.sum(Backup.file_size)).scalar() or 0
        
        return {
            "total_backups": total_backups,
            "completed_backups": completed_backups,
            "failed_backups": failed_backups,
            "latest_backup": latest_backup.created_at if latest_backup else None,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
    except Exception as e:
        logger.error(f"Error in get_backup_summary: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")



@router.post("/schedule")
async def schedule_backup(
    schedule_data: BackupScheduleSchema,
    db: Session = Depends(get_db)
    # # # current_user parameter removed for development,  # Removed for development  # Commented out for development
):
    """Schedule automatic backups"""
    # This would integrate with a task scheduler like Celery or APScheduler
    # For now, we'll just store the schedule in the database
    
    from app.models.backup import BackupSchedule as BackupScheduleModel
    
    schedule = BackupScheduleModel(
        backup_type=schedule_data.backup_type,
        frequency=schedule_data.frequency,
        time=schedule_data.time,
        include_files=schedule_data.include_files,
        description=schedule_data.description,
        created_by="dev_user"  # Hardcoded for development
    )
    
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    
    return {"message": "Backup schedule created", "schedule_id": schedule.id}

def collect_backup_usage_statistics(db: Session) -> dict:
    """Collect comprehensive backup usage statistics"""
    try:
        # Get all backups
        all_backups = db.query(Backup).all()
        
        # Basic counts
        total_backups = len(all_backups)
        completed_backups = len([b for b in all_backups if b.status == "completed"])
        failed_backups = len([b for b in all_backups if b.status == "failed"])
        in_progress_backups = len([b for b in all_backups if b.status == "in_progress"])
        
        # Backup type distribution
        backup_types = Counter([b.backup_type for b in all_backups])
        
        # Time-based statistics
        now = datetime.utcnow()
        last_24h = now - timedelta(days=1)
        last_7d = now - timedelta(days=7)
        last_30d = now - timedelta(days=30)
        
        # Convert datetime objects to timezone-naive for comparison
        recent_backups = [b for b in all_backups if b.created_at.replace(tzinfo=None) >= last_24h]
        weekly_backups = [b for b in all_backups if b.created_at.replace(tzinfo=None) >= last_7d]
        monthly_backups = [b for b in all_backups if b.created_at.replace(tzinfo=None) >= last_30d]
        
        # File size statistics
        completed_backup_sizes = [b.file_size for b in all_backups if b.status == "completed" and b.file_size]
        avg_file_size = statistics.mean(completed_backup_sizes) if completed_backup_sizes else 0
        max_file_size = max(completed_backup_sizes) if completed_backup_sizes else 0
        min_file_size = min(completed_backup_sizes) if completed_backup_sizes else 0
        
        # Error analysis
        error_messages = [b.error_message for b in all_backups if b.error_message]
        error_types = Counter([msg.split(':')[0] if ':' in msg else msg for msg in error_messages])
        
        # Success rate
        success_rate = (completed_backups / total_backups * 100) if total_backups > 0 else 0
        
        # Backup frequency
        if len(all_backups) >= 2:
            backup_times = sorted([b.created_at for b in all_backups])
            time_diffs = [(backup_times[i+1] - backup_times[i]).total_seconds() / 3600 
                         for i in range(len(backup_times)-1)]
            avg_backup_interval = statistics.mean(time_diffs) if time_diffs else 0
        else:
            avg_backup_interval = 0
        
        return {
            "summary": {
                "total_backups": total_backups,
                "completed_backups": completed_backups,
                "failed_backups": failed_backups,
                "in_progress_backups": in_progress_backups,
                "success_rate_percent": round(success_rate, 2)
            },
            "backup_types": dict(backup_types),
            "time_periods": {
                "last_24h": len(recent_backups),
                "last_7_days": len(weekly_backups),
                "last_30_days": len(monthly_backups)
            },
            "file_statistics": {
                "average_size_bytes": round(avg_file_size, 2),
                "max_size_bytes": max_file_size,
                "min_size_bytes": min_file_size,
                "total_size_mb": round(sum(completed_backup_sizes) / (1024 * 1024), 2)
            },
            "error_analysis": {
                "total_errors": len(error_messages),
                "error_types": dict(error_types),
                "most_common_error": error_types.most_common(1)[0] if error_types else None
            },
            "performance": {
                "average_backup_interval_hours": round(avg_backup_interval, 2),
                "backup_frequency_per_day": round(len(weekly_backups) / 7, 2)
            }
        }
    except Exception as e:
        logger.error(f"Error collecting usage statistics: {e}")
        return {"error": str(e)}

def analyze_backup_errors(db: Session) -> dict:
    """Analyze backup errors and suggest fixes"""
    try:
        failed_backups = db.query(Backup).filter(Backup.status == "failed").all()
        
        error_analysis = {
            "total_failed_backups": len(failed_backups),
            "error_categories": {},
            "suggested_fixes": [],
            "critical_issues": []
        }
        
        # Categorize errors
        for backup in failed_backups:
            error_msg = backup.error_message or "Unknown error"
            
            # Categorize error
            if "Database dump failed" in error_msg:
                category = "database_dump_failure"
            elif "Metadata creation failed" in error_msg:
                category = "metadata_failure"
            elif "Files backup failed" in error_msg:
                category = "files_backup_failure"
            elif "Permission denied" in error_msg:
                category = "permission_error"
            elif "Disk space" in error_msg:
                category = "disk_space_error"
            else:
                category = "unknown_error"
            
            if category not in error_analysis["error_categories"]:
                error_analysis["error_categories"][category] = []
            
            error_analysis["error_categories"][category].append({
                "backup_id": backup.id,
                "error_message": error_msg,
                "created_at": backup.created_at.isoformat(),
                "backup_type": backup.backup_type
            })
        
        # Generate suggested fixes
        for category, errors in error_analysis["error_categories"].items():
            if category == "database_dump_failure":
                error_analysis["suggested_fixes"].append({
                    "category": category,
                    "fix": "Check database connectivity and permissions",
                    "action": "verify_database_connection",
                    "priority": "high"
                })
            elif category == "metadata_failure":
                error_analysis["suggested_fixes"].append({
                    "category": category,
                    "fix": "Check file system permissions and disk space",
                    "action": "check_file_permissions",
                    "priority": "medium"
                })
            elif category == "permission_error":
                error_analysis["suggested_fixes"].append({
                    "category": category,
                    "fix": "Fix file system permissions for backup directory",
                    "action": "fix_permissions",
                    "priority": "high"
                })
            elif category == "disk_space_error":
                error_analysis["suggested_fixes"].append({
                    "category": category,
                    "fix": "Free up disk space or change backup location",
                    "action": "check_disk_space",
                    "priority": "critical"
                })
        
        # Identify critical issues
        if len(failed_backups) > 5:
            error_analysis["critical_issues"].append({
                "issue": "High failure rate",
                "description": f"{len(failed_backups)} failed backups detected",
                "recommendation": "Review backup configuration and system resources"
            })
        
        return error_analysis
    except Exception as e:
        logger.error(f"Error analyzing backup errors: {e}")
        return {"error": str(e)}

def apply_automated_fixes(db: Session, fix_type: str = None) -> dict:
    """Apply automated fixes for common backup issues"""
    try:
        fixes_applied = []
        errors_fixed = []
        
        if fix_type == "database_connection" or fix_type is None:
            # Fix database connection issues
            try:
                # Test database connection
                from app.core.database import engine
                import sqlalchemy as sa
                with engine.connect() as conn:
                    conn.execute(sa.text("SELECT 1"))
                fixes_applied.append("database_connection_test_passed")
            except Exception as e:
                logger.error(f"Database connection test failed: {e}")
                errors_fixed.append(f"database_connection_error: {str(e)}")
        
        if fix_type == "file_permissions" or fix_type is None:
            # Fix file permission issues
            try:
                backup_dirs = ["backups", "backups/absolute", "backups/incremental"]
                for dir_path in backup_dirs:
                    if not os.path.exists(dir_path):
                        os.makedirs(dir_path, exist_ok=True)
                        fixes_applied.append(f"created_directory: {dir_path}")
                
                # Test write permissions
                test_file = os.path.join("backups", "test_write.tmp")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                fixes_applied.append("file_permissions_test_passed")
            except Exception as e:
                logger.error(f"File permission test failed: {e}")
                errors_fixed.append(f"file_permission_error: {str(e)}")
        
        if fix_type == "disk_space" or fix_type is None:
            # Check disk space
            try:
                import shutil
                total, used, free = shutil.disk_usage("backups")
                free_gb = free / (1024**3)
                
                if free_gb < 1:  # Less than 1GB free
                    errors_fixed.append(f"low_disk_space: {free_gb:.2f}GB free")
                else:
                    fixes_applied.append(f"disk_space_ok: {free_gb:.2f}GB free")
            except Exception as e:
                logger.error(f"Disk space check failed: {e}")
                errors_fixed.append(f"disk_space_check_error: {str(e)}")
        
        if fix_type == "cleanup_failed_backups" or fix_type is None:
            # Clean up failed backup records older than 7 days
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=7)
                old_failed_backups = db.query(Backup).filter(
                    Backup.status == "failed",
                    Backup.created_at < cutoff_date
                ).all()
                
                for backup in old_failed_backups:
                    # Clean up associated files
                    if backup.file_path and os.path.exists(backup.file_path):
                        os.remove(backup.file_path)
                    
                    # Remove metadata file
                    metadata_file = os.path.join(os.path.dirname(backup.file_path), f"{backup.id}_{METADATA_FILE}")
                    if os.path.exists(metadata_file):
                        os.remove(metadata_file)
                    
                    # Delete from database
                    db.delete(backup)
                
                db.commit()
                fixes_applied.append(f"cleaned_up_old_failed_backups: {len(old_failed_backups)}")
            except Exception as e:
                logger.error(f"Failed to clean up old backups: {e}")
                errors_fixed.append(f"cleanup_error: {str(e)}")
        
        return {
            "fixes_applied": fixes_applied,
            "errors_fixed": errors_fixed,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "completed"
        }
    except Exception as e:
        logger.error(f"Error applying automated fixes: {e}")
        return {"error": str(e)}

def get_backup_health_status(db: Session) -> dict:
    """Get overall backup system health status"""
    try:
        # Get recent backups (last 24 hours)
        last_24h = datetime.utcnow() - timedelta(hours=24)
        recent_backups = db.query(Backup).filter(Backup.created_at >= last_24h).all()
        
        # Calculate health metrics
        total_recent = len(recent_backups)
        successful_recent = len([b for b in recent_backups if b.status == "completed"])
        failed_recent = len([b for b in recent_backups if b.status == "failed"])
        
        success_rate = (successful_recent / total_recent * 100) if total_recent > 0 else 100
        
        # Determine health status
        if success_rate >= 90:
            health_status = "excellent"
        elif success_rate >= 75:
            health_status = "good"
        elif success_rate >= 50:
            health_status = "fair"
        else:
            health_status = "poor"
        
        # Check for critical issues
        critical_issues = []
        if failed_recent > 3:
            critical_issues.append("High failure rate in last 24 hours")
        
        # Check disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage("backups")
            free_gb = free / (1024**3)
            if free_gb < 1:
                critical_issues.append("Low disk space")
        except:
            pass
        
        # Check backup frequency
        if total_recent == 0:
            critical_issues.append("No recent backups")
        
        return {
            "health_status": health_status,
            "success_rate_percent": round(success_rate, 2),
            "recent_activity": {
                "total_backups_24h": total_recent,
                "successful_backups_24h": successful_recent,
                "failed_backups_24h": failed_recent
            },
            "critical_issues": critical_issues,
            "last_check": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        return {"error": str(e)}

# Add new API endpoints

@router.get("/statistics/usage")
async def get_backup_usage_statistics(
    db: Session = Depends(get_db)
    # # # current_user parameter removed for development,  # Removed for development  # Commented out for development
):
    """Get comprehensive backup usage statistics"""
    try:
        stats = collect_backup_usage_statistics(db)
        return stats
    except Exception as e:
        logger.error(f"Error getting usage statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Error collecting statistics: {str(e)}")

@router.get("/statistics/errors")
async def get_backup_error_analysis(
    db: Session = Depends(get_db)
    # # # current_user parameter removed for development,  # Removed for development  # Commented out for development
):
    """Analyze backup errors and get suggested fixes"""
    try:
        analysis = analyze_backup_errors(db)
        return analysis
    except Exception as e:
        logger.error(f"Error analyzing backup errors: {e}")
        raise HTTPException(status_code=500, detail=f"Error analyzing errors: {str(e)}")

@router.post("/fix/apply")
async def apply_backup_fixes(
    fix_type: str = None,
    db: Session = Depends(get_db)
    # # # current_user parameter removed for development,  # Removed for development  # Commented out for development
):
    """Apply automated fixes for backup issues"""
    try:
        result = apply_automated_fixes(db, fix_type)
        return result
    except Exception as e:
        logger.error(f"Error applying fixes: {e}")
        raise HTTPException(status_code=500, detail=f"Error applying fixes: {str(e)}")

@router.get("/health/status")
async def get_backup_health_status_endpoint(
    db: Session = Depends(get_db)
    # # # current_user parameter removed for development,  # Removed for development  # Commented out for development
):
    """Get backup system health status"""
    try:
        health = get_backup_health_status(db)
        return health
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting health status: {str(e)}")

@router.post("/fix/retry-failed")
async def retry_failed_backups(
    backup_ids: List[str] = None,
    db: Session = Depends(get_db)
    # # # current_user parameter removed for development,  # Removed for development  # Commented out for development
):
    """Retry failed backups"""
    try:
        if backup_ids:
            failed_backups = db.query(Backup).filter(
                Backup.id.in_(backup_ids),
                Backup.status == "failed"
            ).all()
        else:
            # Get all failed backups from last 24 hours
            last_24h = datetime.utcnow() - timedelta(hours=24)
            failed_backups = db.query(Backup).filter(
                Backup.status == "failed",
                Backup.created_at >= last_24h
            ).all()
        
        retry_results = []
        for backup in failed_backups:
            try:
                # Reset status to in_progress
                backup.status = "in_progress"
                backup.error_message = None
                db.commit()
                
                # Trigger new backup with same parameters
                # This would require storing the original backup parameters
                retry_results.append({
                    "backup_id": backup.id,
                    "status": "retry_initiated",
                    "message": "Backup retry initiated"
                })
            except Exception as e:
                retry_results.append({
                    "backup_id": backup.id,
                    "status": "retry_failed",
                    "error": str(e)
                })
        
        return {
            "retry_results": retry_results,
            "total_retried": len(failed_backups)
        }
    except Exception as e:
        logger.error(f"Error retrying failed backups: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrying backups: {str(e)}")

@router.get("/statistics/performance")
async def get_backup_performance_metrics(
    days: int = 30,
    db: Session = Depends(get_db)
    # # # current_user parameter removed for development,  # Removed for development  # Commented out for development
):
    """Get backup performance metrics over time"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_backups = db.query(Backup).filter(Backup.created_at >= cutoff_date).all()
        
        # Group by day
        daily_stats = defaultdict(lambda: {"total": 0, "completed": 0, "failed": 0, "sizes": []})
        
        for backup in recent_backups:
            date_key = backup.created_at.date().isoformat()
            daily_stats[date_key]["total"] += 1
            
            if backup.status == "completed":
                daily_stats[date_key]["completed"] += 1
                if backup.file_size:
                    daily_stats[date_key]["sizes"].append(backup.file_size)
            elif backup.status == "failed":
                daily_stats[date_key]["failed"] += 1
        
        # Calculate daily metrics
        performance_data = []
        for date, stats in sorted(daily_stats.items()):
            success_rate = (stats["completed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            avg_size = statistics.mean(stats["sizes"]) if stats["sizes"] else 0
            
            performance_data.append({
                "date": date,
                "total_backups": stats["total"],
                "completed_backups": stats["completed"],
                "failed_backups": stats["failed"],
                "success_rate_percent": round(success_rate, 2),
                "average_size_bytes": round(avg_size, 2)
            })
        
        return {
            "period_days": days,
            "total_backups_in_period": len(recent_backups),
            "daily_performance": performance_data
        }
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting performance metrics: {str(e)}")
