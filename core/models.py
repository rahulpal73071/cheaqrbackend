import uuid
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class AllowedEmail(models.Model):
    email = models.EmailField(unique=True)
    note = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.email

class User(AbstractUser):
    # Use email as username field if you want; for now keep username but require unique email
    email = models.EmailField(unique=True)
    # a stable public id safe to expose via QR payload (not guessable)
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    REQUIRED_FIELDS = ['email']  # when createsuperuser prompts for email

    def __str__(self):
        return f"{self.username} ({self.email})"

class QRToken(models.Model):
    """
    Short-lived token tied to a user for QR scanning.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='qr_tokens')
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    @classmethod
    def create_for_user(cls, user):
        ttl = getattr(settings, 'QR_TOKEN_TTL_MINUTES', 2)
        tok = uuid.uuid4().hex
        now = timezone.now()
        return cls.objects.create(
            user=user,
            token=tok,
            expires_at=now + timedelta(minutes=ttl)
        )

    def is_valid(self):
        return timezone.now() <= self.expires_at

    def __str__(self):
        return f"{self.user_id}:{self.token[:8]}..."

class ItemChoices(models.TextChoices):
    MILK = 'milk', 'Milk'
    TEA = 'tea', 'Tea'
    MEAL = 'meal', 'Meal'

class StatusChoices(models.TextChoices):
    NOT_TAKEN = 'not_taken', 'Not Taken'
    TAKEN = 'taken', 'Taken'
    WAIT = 'wait', 'Wait'

class UserItemStatus(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='item_statuses')
    item = models.CharField(max_length=16, choices=ItemChoices.choices)
    status = models.CharField(max_length=16, choices=StatusChoices.choices, default=StatusChoices.NOT_TAKEN)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'item')

    def __str__(self):
        return f"{self.user.username} - {self.item}: {self.status}"

# ✅ NEW Menu model
class Menu(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class StatusChoices(models.TextChoices):
    NOT_TAKEN = 'not_taken', 'Not Taken'
    TAKEN = 'taken', 'Taken'
    WAIT = 'wait', 'Wait'


class UserItemStatus(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='item_statuses')
    # 🔄 Instead of hardcoded choices → foreign key to Menu
    item = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name='statuses')
    status = models.CharField(max_length=16, choices=StatusChoices.choices, default=StatusChoices.NOT_TAKEN)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'item')

    def __str__(self):
        return f"{self.user.username} - {self.item.name}: {self.status}"