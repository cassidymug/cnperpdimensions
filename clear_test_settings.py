from app.core.database import SessionLocal
from app.models.app_setting import AppSetting

db = SessionLocal()
try:
    # Get or create the singleton app settings
    settings = AppSetting.get_instance(db)

    # Clear test data and set to production-ready defaults
    settings.company_name = ""  # Empty - user should fill this
    settings.app_name = "CNPERP ERP System"
    settings.email = ""  # Empty - user should fill this
    settings.phone = ""  # Empty - user should fill this
    settings.website = ""  # Empty - user should fill this
    settings.address = ""  # Empty - user should fill this

    # Keep important settings
    settings.currency = "BWP"
    settings.vat_rate = 14.0
    settings.default_vat_rate = 14.0
    settings.country = "BW"
    settings.locale = "en"
    settings.timezone = "Africa/Gaborone"
    settings.theme_mode = "light"

    db.commit()
    print("✅ Test data cleared from app_settings")
    print("All business fields set to empty strings (ready for user configuration)")

except Exception as e:
    db.rollback()
    print("❌ Error clearing test data: " + str(e))
finally:
    db.close()
