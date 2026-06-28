from django.db import connection
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import build_report_query
from .serializers import ReportQuerySerializer, ReportRowSerializer


def _run_report(sql, params):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


class ReportListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = ReportQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data

        sql, params = build_report_query(
            filters=data.get("filters", {}),
            search=data.get("search"),
            sort=data.get("sort"),
            direction=data.get("direction"),
            page=data["page"],
            page_size=data["page_size"],
        )

        rows = _run_report(sql, params)
        serialized = ReportRowSerializer(rows, many=True)
        return Response(
            {
                "page": data["page"],
                "page_size": data["page_size"],
                "results": serialized.data,
            }
        )
