from django.contrib.auth.models import User as djUser
from django.db import models
from django.db.models import DO_NOTHING, Q
from jsonfield import JSONField


class User(models.Model):

    def __str__(self):
        return self.user.username

    def __unicode__(self):
        return self.user.username

    ROLE_CHOICES = (
        ("ADMIN", "ADMIN"),  # all permissions
        ("MTURK", "MTURK"),  # local permission and mturk
        ("LOCAL", "LOCAL")  # permissions for local experiment only
    )
    user = models.OneToOneField(djUser, on_delete=models.CASCADE)
    role = models.CharField(
        "user role",
        max_length=100,
        choices=ROLE_CHOICES,
        null=True,
        blank=True,
        help_text="Name of user role.")
