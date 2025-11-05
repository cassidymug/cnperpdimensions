from app.core.database import SessionLocal
from app.models.app_setting import AppSetting

db = SessionLocal()
try:
    settings = AppSetting.get_instance(db)

    print("Current app_settings after clearing test data:")
    print("  Company Name: '" + str(settings.company_name) + "'")
    print("  Email: '" + str(settings.email) + "'")
    print("  Phone: '" + str(settings.phone) + "'")
    print("  Website: '" + str(settings.website) + "'")
    print("  Address: '" + str(settings.address) + "'")
    print("  App Name: '" + str(settings.app_name) + "'")

    if settings.company_name == "" and settings.email == "":
        print("\nTest data successfully cleared!")

finally:
    db.close()
