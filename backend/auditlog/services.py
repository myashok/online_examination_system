from auditlog.models import AuditLog


def record_audit(user, action, entity, entity_id=None, detail=""):
    AuditLog.objects.create(
        user=user if getattr(user, "pk", None) else None,
        action=action,
        entity=entity,
        entity_id=entity_id,
        detail=detail or "",
    )
