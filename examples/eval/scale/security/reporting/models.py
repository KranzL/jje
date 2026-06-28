from django.conf import settings
from django.db import models


class Report(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("archived", "Archived"),
    )

    REGION_CHOICES = (
        ("na", "North America"),
        ("emea", "EMEA"),
        ("apac", "APAC"),
        ("latam", "LATAM"),
    )

    title = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft")
    region = models.CharField(max_length=8, choices=REGION_CHOICES, db_index=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports",
    )
    amount_cents = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reports"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status", "region"]),
        ]

    def __str__(self):
        return f"Report<{self.pk}:{self.title}>"
