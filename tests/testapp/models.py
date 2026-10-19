from django.db import models


class Note(models.Model):
    title = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, blank=True, default="")
    secret = models.CharField(max_length=50, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)
