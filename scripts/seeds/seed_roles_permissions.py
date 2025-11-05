from sqlalchemy.orm import Session
from app.models.role import Role, Permission, RolePermission
from .registry import register

BASE_ROLES = ["super_admin","accountant","manager","cashier","pos_user"]
PERMISSIONS = [
    {"name": "pos.record_sale", "module": "pos", "action": "record", "resource": "sale"},
    {"name": "pos.reconcile", "module": "pos", "action": "reconcile", "resource": "all"},
    {"name": "reports.view", "module": "reports", "action": "view", "resource": "all"},
    {"name": "reports.financial.view", "module": "reports", "action": "view", "resource": "financial"},
    {"name": "reports.performance.view", "module": "reports", "action": "view", "resource": "performance"},
    {"name": "reports.debtors_aging.view", "module": "reports", "action": "view", "resource": "debtors_aging"},
    {"name": "settings.view", "module": "settings", "action": "view", "resource": "all"}
]

@register("roles_permissions")
def seed_roles_permissions(db: Session):
    existing_roles = {r.name for r in db.query(Role).all()}
    for rname in BASE_ROLES:
        if rname not in existing_roles:
            db.add(Role(name=rname))
    db.flush()

    existing_perms = {p.name: p for p in db.query(Permission).all()}
    for perm_data in PERMISSIONS:
        pname = perm_data["name"]
        if pname not in existing_perms:
            perm = Permission(
                name=perm_data["name"],
                module=perm_data["module"],
                action=perm_data["action"],
                resource=perm_data["resource"]
            )
            db.add(perm)
            db.flush()
            existing_perms[pname] = perm

    grant_map = {
        "super_admin": [p["name"] for p in PERMISSIONS],
        "accountant": [p["name"] for p in PERMISSIONS if p["name"].startswith("reports.") or p["name"].startswith("pos.")],
        "manager": [p["name"] for p in PERMISSIONS if p["name"].startswith("reports.")],
        "cashier": [p["name"] for p in PERMISSIONS if p["name"].startswith("pos.")],
        "pos_user": [p["name"] for p in PERMISSIONS if p["name"].startswith("pos.")]
    }
    roles = {r.name: r for r in db.query(Role).all()}
    for role_name, plist in grant_map.items():
        role = roles.get(role_name)
        if not role:
            continue
        for pname in plist:
            perm = existing_perms[pname]
            link = db.query(RolePermission).filter_by(role_id=role.id, permission_id=perm.id).first()
            if not link:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    db.commit()
