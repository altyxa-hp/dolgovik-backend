from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Debt, DebtActivity, UserProfile, Notification


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password', 'password2']

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password': 'Пароли не совпадают'})
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({'email': 'Email уже зарегистрирован'})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            password=validated_data['password'],
        )
        UserProfile.objects.create(user=user)
        return user


class UserSerializer(serializers.ModelSerializer):
    rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'rating', 'rating_count']

    def get_rating(self, obj):
        try:
            return obj.profile.rating
        except Exception:
            return None

    def get_rating_count(self, obj):
        try:
            return obj.profile.rating_count
        except Exception:
            return 0


class NotificationSerializer(serializers.ModelSerializer):
    notif_type_display = serializers.CharField(source='get_notif_type_display', read_only=True)
    debt_id = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'notif_type', 'notif_type_display', 'title', 'body',
                  'is_read', 'debt_id', 'created_at']

    def get_debt_id(self, obj):
        return str(obj.debt.id) if obj.debt else None


class DebtActivitySerializer(serializers.ModelSerializer):
    event_display = serializers.CharField(source='get_event_display', read_only=True)

    class Meta:
        model = DebtActivity
        fields = ['id', 'event', 'event_display', 'note', 'created_at']


class DebtSerializer(serializers.ModelSerializer):
    debt_type_display = serializers.CharField(source='get_debt_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    share_url = serializers.ReadOnlyField()
    activities = DebtActivitySerializer(many=True, read_only=True)
    counterpart_name = serializers.SerializerMethodField()
    counterpart_rating = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Debt
        fields = [
            'id', 'debt_type', 'debt_type_display',
            'status', 'status_display',
            'person_name', 'counterpart_email', 'counterpart_name',
            'counterpart_rating', 'owner_name',
            'amount', 'currency', 'note', 'due_date',
            'share_token', 'share_url',
            'link_viewed', 'link_viewed_at',
            'rating',
            'created_at', 'updated_at', 'closed_at',
            'activities',
        ]
        read_only_fields = [
            'id', 'share_token', 'share_url',
            'link_viewed', 'link_viewed_at',
            'created_at', 'updated_at', 'closed_at',
        ]

    def get_counterpart_name(self, obj):
        if obj.counterpart:
            name = f"{obj.counterpart.first_name} {obj.counterpart.last_name}".strip()
            return name or obj.counterpart.email
        return None

    def get_counterpart_rating(self, obj):
        if obj.counterpart:
            try:
                return obj.counterpart.profile.rating
            except Exception:
                return None
        return None

    def get_owner_name(self, obj):
        name = f"{obj.owner.first_name} {obj.owner.last_name}".strip()
        return name or obj.owner.email


class DebtCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Debt
        fields = ['debt_type', 'person_name', 'counterpart_email',
                  'amount', 'currency', 'note', 'due_date']


class PublicDebtSerializer(serializers.ModelSerializer):
    class Meta:
        model = Debt
        fields = ['person_name', 'amount', 'currency', 'note', 'due_date', 'debt_type', 'created_at']
