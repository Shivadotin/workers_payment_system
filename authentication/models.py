from django.db import models
from django.conf import settings
import uuid

class ResetPasword(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.CASCADE)
    reset_id = models.UUIDField(default = uuid.uuid4  , unique = True , editable = False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'password reset for { self.user.username } at { self.created_at}'

