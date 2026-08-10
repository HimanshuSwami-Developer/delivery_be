from django.db import models


class ActiveManager(models.Manager):
    """Default manager — hides soft-deleted rows."""

    def get_queryset(self):
        return super().get_queryset().filter(is_delete=False)


class BaseModel(models.Model):
    """
    Abstract base with common bookkeeping fields.
    Inherit this in any model that needs soft-delete + timestamps.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_delete = models.BooleanField(default=False)

    # objects: excludes soft-deleted rows (use this everywhere by default)
    objects = ActiveManager()
    # all_objects: includes soft-deleted rows (use for admin / recovery / audits)
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self):
        self.is_delete = True
        self.is_active = False
        self.save(update_fields=["is_delete", "is_active", "updated_at"])