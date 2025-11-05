from sqlalchemy.orm import Session
from app.models.inventory import UnitOfMeasure
from .registry import register

# (name, abbreviation, category, subcategory)
UNITS = [
    ("Unit", "UN", "quantity", "basic"),
    ("Kilogram", "KG", "weight", "metric"),
    ("Gram", "G", "weight", "metric"),
    ("Litre", "L", "volume", "metric"),
    ("Millilitre", "ML", "volume", "metric"),
    ("Meter", "M", "length", "metric"),
    ("Centimeter", "CM", "length", "metric"),
    ("Box", "BOX", "quantity", "packaging")
]

@register("units")
def seed_units(db: Session):
    existing = {u.abbreviation: u for u in db.query(UnitOfMeasure).all()}
    added = 0
    for name, abbr, category, subcategory in UNITS:
        if abbr not in existing:
            db.add(UnitOfMeasure(
                name=name,
                abbreviation=abbr,
                category=category,
                subcategory=subcategory,
                is_system_unit=True,
                is_active=True
            ))
            added += 1
    if added:
        db.commit()
