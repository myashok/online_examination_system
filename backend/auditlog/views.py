from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin
from auditlog.models import AuditLog
from auditlog.serializers import AuditLogSerializer


class AuditLogListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        logs = AuditLog.objects.select_related("user").all().order_by("-at", "-id")
        action = request.query_params.get("action")
        user_id = request.query_params.get("user")
        entity = request.query_params.get("entity")
        if action:
            logs = logs.filter(action=action)
        if user_id:
            logs = logs.filter(user_id=user_id)
        if entity:
            logs = logs.filter(entity=entity)
        return Response(AuditLogSerializer(logs[:500], many=True).data)
