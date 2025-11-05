"""
Utility to install sample dot matrix templates

This script installs predefined sample templates into the database
for immediate use with the dot matrix invoice system.
"""

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.app_setting import AppSetting
from app.templates.dot_matrix_samples import SAMPLE_TEMPLATES
import json


def install_sample_templates(db: Session):
    """Install sample dot matrix templates into the database"""
    installed_count = 0
    
    for template_key, template_data in SAMPLE_TEMPLATES.items():
        try:
            # Template content
            content_key = f"dot_matrix_template_{template_key}"
            existing_template = db.query(AppSetting).filter(AppSetting.key == content_key).first()
            
            if not existing_template:
                template_setting = AppSetting(
                    key=content_key,
                    value=template_data['template'],
                    description=f"Sample template: {template_data['name']}"
                )
                db.add(template_setting)
            
            # Template settings
            settings_key = f"dot_matrix_settings_{template_key}"
            existing_settings = db.query(AppSetting).filter(AppSetting.key == settings_key).first()
            
            if not existing_settings:
                settings_setting = AppSetting(
                    key=settings_key,
                    value=json.dumps(template_data['settings']),
                    description=f"Settings for template: {template_data['name']}"
                )
                db.add(settings_setting)
            
            installed_count += 1
            
        except Exception as e:
            print(f"Error installing template {template_key}: {e}")
    
    try:
        db.commit()
        print(f"✅ Successfully installed {installed_count} sample templates")
        return True
    except Exception as e:
        db.rollback()
        print(f"❌ Error committing templates: {e}")
        return False


def list_installed_templates(db: Session):
    """List all installed dot matrix templates"""
    templates = db.query(AppSetting).filter(
        AppSetting.key.like('dot_matrix_template_%')
    ).all()
    
    print(f"\n📋 Installed Dot Matrix Templates ({len(templates)}):")
    print("=" * 50)
    
    for template in templates:
        template_name = template.key.replace('dot_matrix_template_', '')
        print(f"• {template_name}: {template.description}")
    
    return templates


def remove_sample_templates(db: Session):
    """Remove all sample templates from database"""
    try:
        # Remove template content
        content_count = db.query(AppSetting).filter(
            AppSetting.key.like('dot_matrix_template_%')
        ).delete(synchronize_session=False)
        
        # Remove template settings
        settings_count = db.query(AppSetting).filter(
            AppSetting.key.like('dot_matrix_settings_%')
        ).delete(synchronize_session=False)
        
        db.commit()
        print(f"✅ Removed {content_count} templates and {settings_count} settings")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error removing templates: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    # Get database session
    db = next(get_db())
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "install":
            install_sample_templates(db)
            list_installed_templates(db)
            
        elif command == "list":
            list_installed_templates(db)
            
        elif command == "remove":
            confirm = input("Are you sure you want to remove all templates? (y/N): ")
            if confirm.lower() == 'y':
                remove_sample_templates(db)
            else:
                print("Operation cancelled")
                
        else:
            print("Usage: python install_sample_templates.py [install|list|remove]")
    else:
        print("Dot Matrix Template Manager")
        print("=" * 30)
        print("1. Install sample templates")
        print("2. List installed templates")
        print("3. Remove all templates")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            install_sample_templates(db)
            list_installed_templates(db)
        elif choice == "2":
            list_installed_templates(db)
        elif choice == "3":
            confirm = input("Are you sure you want to remove all templates? (y/N): ")
            if confirm.lower() == 'y':
                remove_sample_templates(db)
        elif choice == "4":
            print("Goodbye!")
        else:
            print("Invalid choice")
    
    db.close()
