from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import get_db, engine
from app.models import Base
from app.api.v1.api import api_router
from app.api.v1.endpoints import landed_costs
from app.api.v1.endpoints import branch_sales_realtime
import app.api.accounting_codes  # Force import to ensure router is loaded
from app.core.security import verify_token
from app.core.database import SessionLocal
from app.models.role import Permission
from scripts.seeds import registry as seed_registry  # Plan A seeds
import scripts.seeds.seed_roles_permissions  # noqa
import scripts.seeds.seed_units  # noqa
import scripts.seeds.seed_accounts  # noqa
import scripts.seeds.seed_demo_users  # noqa
from sqlalchemy import text
from app.services.ifrs_reporting_service import IFRSReportingService

# Create database tables (note: tiny edit to trigger reload)
Base.metadata.create_all(bind=engine)

# Security
security = HTTPBearer()


def apply_ifrs_core_tags(db: Session) -> None:
    """Assign IFRS reporting_tag to accounting codes when missing or invalid."""
    from app.models.accounting import AccountingCode

    try:
        accounts = db.query(AccountingCode).all()
        updates = 0
        reviewed = 0
        manual_review = []

        for account in accounts:
            reviewed += 1
            current_tag = (account.reporting_tag or "").strip()
            recommended_tag = IFRSReportingService.determine_tag_for_account(account)
            current_valid = IFRSReportingService.validate_reporting_tag(current_tag)

            if recommended_tag and recommended_tag != current_tag:
                account.reporting_tag = recommended_tag
                updates += 1
            elif not current_valid and recommended_tag:
                account.reporting_tag = recommended_tag
                updates += 1
            elif not current_valid and not recommended_tag:
                manual_review.append(account)

        if updates:
            db.commit()

        remaining = db.query(AccountingCode).filter(
            (AccountingCode.reporting_tag.is_(None))
            | (AccountingCode.reporting_tag.notin_(IFRSReportingService.VALID_IFRS_TAGS))
        ).count()

        if updates:
            msg_suffix = (
                f", but {remaining} accounts still need manual classification"
                if remaining
                else ""
            )
            print(f"[IFRS] Assigned or corrected reporting tags for {updates} of {reviewed} accounts{msg_suffix}")
        elif remaining == 0:
            print("[IFRS] All accounting codes already have valid IFRS tags")

        if manual_review:
            preview = ", ".join(
                f"{acct.code} ({acct.name})"
                for acct in manual_review[:5]
            )
            extra = "..." if len(manual_review) > 5 else ""
            print(
                f"[IFRS] {len(manual_review)} accounts still need manual classification: {preview}{extra}"
            )
    except Exception as exc:
        db.rollback()
        print(f"[IFRS] Startup tagging failed: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("Starting CNPERP ERP System...")
    # Ensure DB connection pool is fresh (important after enum/type migrations)
    try:
        engine.dispose()
        print("[INIT] Disposed SQLAlchemy engine pool to refresh DB type caches")
    except Exception as de:
        print(f"[INIT] Engine dispose warning: {de}")
    # Seed core POS permissions if missing
    db = SessionLocal()
    try:
        needed = [
            ("pos.record_sale","POS record sale","pos","record_sale","all"),
            ("pos.reconcile","POS reconciliation","pos","reconcile","all")
        ]
        existing = {p.name for p in db.query(Permission).filter(Permission.name.in_([n for n,_,_,_,_ in needed])).all()}
        new = 0
        for name, desc, module, action, resource in needed:
            if name not in existing:
                db.add(Permission(name=name, description=desc, module=module, action=action, resource=resource))
                new += 1
        if new:
            db.commit()
            print(f"[INIT] Seeded {new} POS permissions")
        # Run unified Plan A baseline seeds (idempotent)
        try:
            from scripts.seeds.registry import run_selected
            # Seed baseline plus demo users to enable initial login
            run_selected(db, ["roles_permissions","units","accounts","demo_users"])
            print("[INIT] Baseline Plan A seeds applied")
        except Exception as se:
            print(f"[INIT] Baseline seeding error: {se}")

        # Ensure app_settings singleton exists
        try:
            from app.models.app_setting import AppSetting
            instance = db.query(AppSetting).first()
            if not instance:
                print("[INIT] Creating app_settings singleton...")
                instance = AppSetting()
                db.add(instance)
                db.commit()
                print("[INIT] App settings created successfully")
            else:
                print("[INIT] App settings already exists")
        except Exception as ase:
            print(f"[INIT] App settings creation error: {ase}")

        # Ensure product_assemblies has unit_of_measure_id (idempotent quick migration)
        try:
            print("[INIT] Ensuring product_assemblies.unit_of_measure_id column exists...")
            with engine.connect() as conn:
                exists = conn.execute(text(
                    "SELECT 1 FROM information_schema.columns WHERE table_name='product_assemblies' AND column_name='unit_of_measure_id'"
                )).first()
                if not exists:
                    conn.execute(text("ALTER TABLE product_assemblies ADD COLUMN IF NOT EXISTS unit_of_measure_id VARCHAR NULL"))
                    print("[INIT] Added column unit_of_measure_id to product_assemblies")
                # Ensure FK exists
                fk_exists = conn.execute(text(
                    "SELECT 1 FROM information_schema.table_constraints WHERE table_name='product_assemblies' AND constraint_name='fk_product_assemblies_unit_of_measure_id'"
                )).first()
                if not fk_exists:
                    conn.execute(text(
                        "ALTER TABLE product_assemblies ADD CONSTRAINT fk_product_assemblies_unit_of_measure_id FOREIGN KEY (unit_of_measure_id) REFERENCES unit_of_measures(id) ON DELETE SET NULL"
                    ))
                    print("[INIT] Added FK fk_product_assemblies_unit_of_measure_id")
                conn.commit()
            print("[INIT] product_assemblies schema OK")
        except Exception as me:
            print(f"[INIT] Quick migration check failed (non-fatal): {me}")

        apply_ifrs_core_tags(db)

    except Exception as e:
        print(f"[INIT] Permission seeding failed: {e}")
    finally:
        db.close()
    yield
    # Shutdown
    print("Shutting down CNPERP ERP System...")


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title=settings.app_name,
        description="Comprehensive ERP System for Business Management",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count"],
    )

    # Mount static files
    import os
    # Use absolute path to static directory
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(landed_costs.router, prefix="/api/v1/landed-costs", tags=["Landed Costs"])
    app.include_router(branch_sales_realtime.router, tags=["Branch Sales"])

    # Include VAT router
    from app.api.v1 import vat as vat_router
    app.include_router(vat_router.router, prefix="/api/v1/vat", tags=["VAT"])

    # Include Accounting Dimensions router
    from app.routers.accounting_dimensions import router as dimensions_router
    app.include_router(dimensions_router, tags=["Accounting Dimensions"])

    # Include Dimensional Reports router (replaces old reports system)
    from app.routers.dimensional_reports import router as dimensional_reports_router
    app.include_router(dimensional_reports_router, tags=["Dimensional Reports"])

    # Include Banking Dimensions router (Phase 4: Dimensional Banking)
    from app.routers.banking_dimensions import router as banking_dimensions_router
    app.include_router(banking_dimensions_router, tags=["Banking Dimensions"])

    # Print all registered routes for diagnostics
    print("[DEBUG] Registered routes:")
    for route in app.routes:
        print(f"[DEBUG] {route.path} -> {getattr(route, 'methods', None)}")

    @app.get("/")
    async def root():
        return {
            "message": "Welcome to CNPERP ERP System",
            "version": "1.0.0",
            "docs": "/docs",
            "frontend": "/static/index.html"
        }

    # Standardize 403 responses for frontend handling
    from fastapi.responses import JSONResponse
    from starlette.requests import Request
    from starlette.status import HTTP_403_FORBIDDEN

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        if exc.status_code == HTTP_403_FORBIDDEN:
            return JSONResponse(
                status_code=HTTP_403_FORBIDDEN,
                content={
                    "success": False,
                    "error": "forbidden",
                    "message": exc.detail or "Forbidden",
                    "path": request.url.path
                }
            )
        # default fallback
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": "http_error",
                "message": exc.detail,
                "path": request.url.path
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        import traceback
        error_detail = f"{exc.__class__.__name__}: {str(exc)}"
        traceback.print_exc()
        print(f"[ERROR] {request.method} {request.url.path}: {error_detail}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": exc.__class__.__name__,
                "message": str(exc),
                "path": request.url.path
            }
        )

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": settings.app_name, "build": "asset-enum-fix-1"}

    @app.get("/health/db")
    async def health_db():
        """Database health check: runs SELECT 1 and returns server version and connectivity status."""
        from sqlalchemy import text
        info = {"service": "database", "configured_url": str(engine.url).rsplit('@',1)[-1] if hasattr(engine, 'url') else "unknown"}
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                version = conn.execute(text("SELECT version()"))
                info.update(status="ok", reachable=True, version=version.scalar())
        except Exception as e:
            info.update(status="error", reachable=False, error=str(e))
        return info

    @app.get("/health/redis")
    async def redis_health():
        from app.core.cache import get_redis
        info = {"service": "redis", "configured_url": settings.redis_url}
        try:
            r = get_redis()
            if r is None:
                info.update(status="unavailable", reachable=False)
            else:
                pong = r.ping()
                info.update(status="ok" if pong else "degraded", reachable=bool(pong))
                try:
                    info['dbsize'] = r.dbsize()
                except Exception:
                    pass
        except Exception as e:
            info.update(status="error", error=str(e), reachable=False)
        return info

    @app.get("/metrics")
    async def metrics():
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        from fastapi import Response
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

    @app.get("/dashboard")
    async def dashboard():
        """Redirect to the main dashboard"""
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/static/index.html")

    @app.get("/backup-management")
    async def backup_management():
        """Serve the backup management page"""
        from fastapi.responses import FileResponse
        import os
        backup_path = os.path.abspath("app/static/backup-management.html")
        return FileResponse(backup_path)

    @app.get("/management-reports")
    async def management_reports():
        """Serve the management reports page"""
        from fastapi.responses import FileResponse
        import os
        reports_path = os.path.abspath("app/static/management-reports.html")
        return FileResponse(reports_path)

    @app.get("/role-management")
    async def role_management():
        """Serve the role management page"""
        from fastapi.responses import FileResponse
        import os
        role_path = os.path.abspath("app/static/role-management.html")
        return FileResponse(role_path)

    @app.get("/help-center")
    async def help_center():
        """Serve the help center page"""
        from fastapi.responses import FileResponse
        import os
        help_path = os.path.abspath("app/static/help-center.html")
        return FileResponse(help_path)

    @app.get("/complete-user-guide.html")
    async def complete_user_guide():
        """Serve the complete user guide page"""
        from fastapi.responses import FileResponse
        import os
        guide_path = os.path.abspath("app/static/complete-user-guide.html")
        return FileResponse(guide_path)

    @app.get("/test-static")
    async def test_static():
        """Test static file serving"""
        from fastapi.responses import FileResponse
        import os
        static_path = os.path.abspath("app/static/index.html")
        if os.path.exists(static_path):
            return FileResponse(static_path)
        else:
            return {"error": f"File not found: {static_path}", "cwd": os.getcwd()}

    @app.get("/frontend")
    async def frontend():
        """Serve the main frontend directly"""
        from fastapi.responses import FileResponse
        import os
        static_path = os.path.abspath("app/static/index.html")
        return FileResponse(static_path)

    @app.get("/debug-static")
    async def debug_static():
        """Debug static file serving"""
        import os
        static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
        index_path = os.path.join(static_dir, "index.html")
        return {
            "static_dir": static_dir,
            "static_dir_exists": os.path.exists(static_dir),
            "index_path": index_path,
            "index_exists": os.path.exists(index_path),
            "cwd": os.getcwd(),
            "files_in_static": os.listdir(static_dir) if os.path.exists(static_dir) else []
        }

    @app.get("/static/{file_path:path}")
    async def serve_static_file(file_path: str):
        """Serve static files directly"""
        import os
        static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
        file_path = os.path.join(static_dir, file_path)

        if os.path.exists(file_path) and os.path.isfile(file_path):
            from fastapi.responses import FileResponse
            return FileResponse(file_path)
        else:
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    return app


app = create_application()


# Global authentication dependency removed - authentication is now handled per-endpoint


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
