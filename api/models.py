import uuid
from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, null=True)
    rating_sum = models.FloatField(default=0)
    rating_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def rating(self):
        if self.rating_count == 0:
            return None
        return round(self.rating_sum / self.rating_count, 1)

    def __str__(self):
        return f"Профиль: {self.user.email}"


class Notification(models.Model):
    """Внутренние уведомления в приложении"""
    TYPE_CHOICES = [
        ('debt_created', 'Новый долг'),
        ('debt_approved', 'Долг одобрен'),
        ('debt_rejected', 'Долг отклонён'),
        ('close_requested', 'Запрос на закрытие'),
        ('debt_closed', 'Долг закрыт'),
        ('reminder', 'Напоминание о сроке'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notif_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    debt = models.ForeignKey('Debt', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.email} — {self.title}"


class Debt(models.Model):
    TYPE_CHOICES = [
        ('gave', 'Я дал в долг'),
        ('took', 'Я взял в долг'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Ожидает одобрения'),
        ('active', 'Активный'),
        ('rejected', 'Отклонён'),
        ('close_requested', 'Запрос на закрытие'),
        ('closed', 'Закрыт'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='debts')
    counterpart = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='counterpart_debts'
    )
    counterpart_email = models.EmailField(blank=True, null=True)
    person_name = models.CharField(max_length=150)

    debt_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=5, default='KGS')
    note = models.TextField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)

    share_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    link_viewed = models.BooleanField(default=False)
    link_viewed_at = models.DateTimeField(blank=True, null=True)

    close_requested_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='close_requests'
    )
    rating = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_debt_type_display()} — {self.person_name} — {self.amount}"

    @property
    def share_url(self):
        return f"/api/public/debt/{self.share_token}/"


class DebtActivity(models.Model):
    EVENT_CHOICES = [
        ('created', 'Создан'),
        ('approved', 'Одобрен'),
        ('rejected', 'Отклонён'),
        ('link_viewed', 'Ссылка открыта'),
        ('close_requested', 'Запрос на закрытие'),
        ('closed', 'Закрыт'),
        ('rated', 'Оценён'),
    ]

    debt = models.ForeignKey(Debt, on_delete=models.CASCADE, related_name='activities')
    event = models.CharField(max_length=20, choices=EVENT_CHOICES)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
