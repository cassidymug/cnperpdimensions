from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.app_setting import AppSetting
import base64

router = APIRouter()

@router.post("/upload-logo", summary="Upload company logo for invoices")
async def upload_logo(db: Session = Depends(get_db), logo: UploadFile = File(...)):
    """
    Uploads a company logo and saves it as a base64 string in the app settings.
    """
    # Ensure there's a single AppSetting record
    settings = db.query(AppSetting).first()
    if not settings:
        settings = AppSetting()
        db.add(settings)
        db.commit()
        db.refresh(settings)

    # Read the image and encode it
    contents = await logo.read()
    encoded_logo = base64.b64encode(contents).decode("utf-8")
    
    # Save the base64 string to the database
    settings.company_logo_base64 = f"data:{logo.content_type};base64,{encoded_logo}"
    
    db.commit()
    
    return {"message": "Logo uploaded successfully", "logo_base64": settings.company_logo_base64}
