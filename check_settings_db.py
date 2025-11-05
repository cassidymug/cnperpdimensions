from app.core.database import SessionLocal
from app.models.app_setting import AppSetting

db = SessionLocal()
try:
    settings = db.query(AppSetting).first()
    if settings:
        print('✅ App settings record exists')
        print('  Company Name: ' + str(settings.company_name))
        print('  Email: ' + str(settings.email))
        print('  Phone: ' + str(settings.phone))
        print('  Address: ' + str(settings.address))
    else:
        print('❌ No app settings record in database')
except Exception as e:
    print('Error querying database: ' + str(e))
finally:
    db.close()
