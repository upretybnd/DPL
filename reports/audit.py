from .models import AuditLog


def log_audit(actor, action, entity_type, entity_id, branch=None, details=""):
    AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id or 0,
        branch=branch,
        details=str(details)[:1500],
    )
