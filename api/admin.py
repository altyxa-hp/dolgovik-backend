from django.contrib import admin
from .models import Debt, DebtActivity, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'created_at']


class DebtActivityInline(admin.TabularInline):
    model = DebtActivity
    extra = 0
    readonly_fields = ['event', 'note', 'created_at']


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = ['person_name', 'owner', 'debt_type', 'amount', 'currency', 'status', 'created_at']
    list_filter = ['debt_type', 'status', 'currency']
    search_fields = ['person_name', 'owner__email']
    inlines = [DebtActivityInline]
    readonly_fields = ['id', 'share_token', 'link_viewed', 'link_viewed_at', 'created_at']


@admin.register(DebtActivity)
class DebtActivityAdmin(admin.ModelAdmin):
    list_display = ['debt', 'event', 'created_at']
    list_filter = ['event']
