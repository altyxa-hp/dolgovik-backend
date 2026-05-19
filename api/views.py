from django.utils import timezone
from django.db.models import Sum, Q
from django.contrib.auth.models import User
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Debt, DebtActivity, UserProfile, Notification
from .serializers import (
    RegisterSerializer, UserSerializer,
    DebtSerializer, DebtCreateSerializer,
    PublicDebtSerializer, NotificationSerializer,
)


def send_notification(recipient, notif_type, title, body, debt=None):
    """Создать внутреннее уведомление"""
    Notification.objects.create(
        recipient=recipient,
        notif_type=notif_type,
        title=title,
        body=body,
        debt=debt,
    )


# ── Авторизация ──────────────────────────────────────────────────

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def me_view(request):
    return Response(UserSerializer(request.user).data)


# ── Пункт 2: Проверка email — зарегистрирован ли пользователь ───

@api_view(['GET'])
def check_user(request):
    """GET /api/users/check/?email=test@mail.com"""
    email = request.query_params.get('email', '').strip()
    if not email:
        return Response({'exists': False})
    try:
        user = User.objects.get(email=email)
        name = f"{user.first_name} {user.last_name}".strip() or user.email
        return Response({'exists': True, 'name': name})
    except User.DoesNotExist:
        return Response({'exists': False})


# ── Уведомления ──────────────────────────────────────────────────

@api_view(['GET'])
def notifications_view(request):
    """GET /api/notifications/ — все уведомления пользователя"""
    notifs = Notification.objects.filter(recipient=request.user)
    return Response(NotificationSerializer(notifs, many=True).data)


@api_view(['POST'])
def mark_read(request, pk):
    """POST /api/notifications/<id>/read/ — пометить прочитанным"""
    try:
        notif = Notification.objects.get(pk=pk, recipient=request.user)
        notif.is_read = True
        notif.save()
        return Response({'ok': True})
    except Notification.DoesNotExist:
        return Response({'error': 'Не найдено'}, status=404)


@api_view(['POST'])
def mark_all_read(request):
    """POST /api/notifications/read-all/ — все прочитаны"""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return Response({'ok': True})


# ── Долги ────────────────────────────────────────────────────────

class DebtListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DebtCreateSerializer
        return DebtSerializer

    def get_queryset(self):
        qs = Debt.objects.filter(owner=self.request.user)
        debt_type = self.request.query_params.get('type')
        status_filter = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        if debt_type:
            qs = qs.filter(debt_type=debt_type)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if search:
            qs = qs.filter(Q(person_name__icontains=search) | Q(note__icontains=search))
        return qs

    def perform_create(self, serializer):
        counterpart_email = self.request.data.get('counterpart_email', '').strip()
        counterpart = None
        debt_status = 'active'
        person_name = self.request.data.get('person_name', '').strip()
        debt_type = self.request.data.get('debt_type')

        if counterpart_email:
            try:
                counterpart = User.objects.get(email=counterpart_email)
                real_name = f"{counterpart.first_name} {counterpart.last_name}".strip()
                if real_name:
                    person_name = real_name
                if debt_type == 'took':
                    debt_status = 'pending'
            except User.DoesNotExist:
                pass

        debt = serializer.save(
            owner=self.request.user,
            counterpart=counterpart,
            person_name=person_name,
            status=debt_status,
        )
        DebtActivity.objects.create(debt=debt, event='created')

        # Пункт 1: уведомление должнику/кредитору
        owner_name = f"{self.request.user.first_name} {self.request.user.last_name}".strip() or self.request.user.email
        if counterpart:
            if debt_type == 'took':
                send_notification(
                    recipient=counterpart,
                    notif_type='debt_created',
                    title='Запрос на подтверждение долга',
                    body=f'{owner_name} указал что взял у вас {debt.amount} {debt.currency}. Подтвердите или отклоните.',
                    debt=debt,
                )
            else:
                send_notification(
                    recipient=counterpart,
                    notif_type='debt_created',
                    title='Вам дали в долг',
                    body=f'{owner_name} записал что дал вам {debt.amount} {debt.currency}.',
                    debt=debt,
                )


class DebtDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DebtSerializer

    def get_queryset(self):
        return Debt.objects.filter(owner=self.request.user)


# ── Входящие запросы на одобрение ────────────────────────────────

@api_view(['GET'])
def incoming_requests(request):
    debts = Debt.objects.filter(counterpart=request.user, status='pending')
    return Response(DebtSerializer(debts, many=True).data)


@api_view(['POST'])
def approve_debt(request, pk):
    try:
        debt = Debt.objects.get(pk=pk, counterpart=request.user, status='pending')
    except Debt.DoesNotExist:
        return Response({'error': 'Запрос не найден'}, status=404)

    debt.status = 'active'
    debt.save()
    DebtActivity.objects.create(debt=debt, event='approved')

    # Зеркальный долг у кредитора
    owner_name = f"{debt.owner.first_name} {debt.owner.last_name}".strip() or debt.owner.email
    approver_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.email
    mirror = Debt.objects.create(
        owner=request.user,
        counterpart=debt.owner,
        person_name=owner_name,
        debt_type='gave',
        status='active',
        amount=debt.amount,
        currency=debt.currency,
        note=debt.note,
        due_date=debt.due_date,
    )
    DebtActivity.objects.create(debt=mirror, event='approved')

    # Уведомление заёмнику
    send_notification(
        recipient=debt.owner,
        notif_type='debt_approved',
        title='Долг одобрен',
        body=f'{approver_name} одобрил долг на {debt.amount} {debt.currency}.',
        debt=debt,
    )
    return Response({'message': 'Долг одобрен'})


@api_view(['POST'])
def reject_debt(request, pk):
    try:
        debt = Debt.objects.get(pk=pk, counterpart=request.user, status='pending')
    except Debt.DoesNotExist:
        return Response({'error': 'Запрос не найден'}, status=404)

    debt.status = 'rejected'
    debt.save()
    DebtActivity.objects.create(debt=debt, event='rejected')

    rejector_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.email
    send_notification(
        recipient=debt.owner,
        notif_type='debt_rejected',
        title='Долг отклонён',
        body=f'{rejector_name} отклонил запрос на долг {debt.amount} {debt.currency}.',
        debt=debt,
    )
    return Response({'message': 'Долг отклонён'})


# ── Пункт 3: Закрытие долга ─────────────────────────────────────
# Заёмник (took) закрывает сам без согласия.
# Кредитор (gave) — запрашивает закрытие, заёмник подтверждает.

@api_view(['POST'])
def request_close(request, pk):
    # Ищем долг у владельца или у counterpart
    debt = None
    try:
        debt = Debt.objects.get(pk=pk, owner=request.user, status__in=['active', 'close_requested'])
    except Debt.DoesNotExist:
        try:
            debt = Debt.objects.get(pk=pk, counterpart=request.user, status__in=['active', 'close_requested'])
        except Debt.DoesNotExist:
            return Response({'error': 'Долг не найден'}, status=404)

    rating = request.data.get('rating')

    # Пункт 3: если это заёмник (took у owner) — закрывает сразу
    is_borrower = (debt.owner == request.user and debt.debt_type == 'took')
    is_lender_counterpart = (debt.counterpart == request.user)

    if is_borrower:
        # Заёмник закрывает без согласия
        debt.status = 'closed'
        debt.closed_at = timezone.now()
        if rating:
            debt.rating = int(rating)
        debt.save()
        DebtActivity.objects.create(debt=debt, event='closed')

        if debt.counterpart:
            send_notification(
                recipient=debt.counterpart,
                notif_type='debt_closed',
                title='Долг закрыт',
                body=f'{debt.person_name} закрыл долг на {debt.amount} {debt.currency}.',
                debt=debt,
            )
        return Response({'message': 'Долг закрыт', 'debt': DebtSerializer(debt).data})

    # Если вторая сторона уже запросила — закрываем
    if debt.status == 'close_requested' and debt.close_requested_by != request.user:
        debt.status = 'closed'
        debt.closed_at = timezone.now()
        if rating:
            debt.rating = int(rating)
            other = debt.close_requested_by
            try:
                profile = other.profile
                profile.rating_sum += int(rating)
                profile.rating_count += 1
                profile.save()
            except Exception:
                pass
        debt.save()
        DebtActivity.objects.create(debt=debt, event='closed',
                                    note=f'Рейтинг: {rating}' if rating else None)

        send_notification(
            recipient=debt.close_requested_by,
            notif_type='debt_closed',
            title='Долг закрыт',
            body=f'Долг на {debt.amount} {debt.currency} подтверждён и закрыт.',
            debt=debt,
        )
        return Response({'message': 'Долг закрыт', 'debt': DebtSerializer(debt).data})

    # Первый запрос на закрытие
    debt.status = 'close_requested'
    debt.close_requested_by = request.user
    debt.save()
    DebtActivity.objects.create(debt=debt, event='close_requested')

    # Уведомляем вторую сторону
    other_user = debt.counterpart if debt.owner == request.user else debt.owner
    requester_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.email
    if other_user:
        send_notification(
            recipient=other_user,
            notif_type='close_requested',
            title='Запрос на закрытие долга',
            body=f'{requester_name} запрашивает закрытие долга на {debt.amount} {debt.currency}.',
            debt=debt,
        )
    return Response({'message': 'Запрос на закрытие отправлен второй стороне'})


@api_view(['GET'])
def close_requests(request):
    debts = Debt.objects.filter(
        status='close_requested'
    ).filter(
        Q(owner=request.user) | Q(counterpart=request.user)
    ).exclude(close_requested_by=request.user)
    return Response(DebtSerializer(debts, many=True).data)


# ── Публичная ссылка ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def public_debt_view(request, token):
    try:
        debt = Debt.objects.get(share_token=token)
    except Debt.DoesNotExist:
        return Response({'error': 'Долг не найден'}, status=404)
    if not debt.link_viewed:
        debt.link_viewed = True
        debt.link_viewed_at = timezone.now()
        debt.save()
        DebtActivity.objects.create(debt=debt, event='link_viewed')
    return Response(PublicDebtSerializer(debt).data)


# ── Статистика ───────────────────────────────────────────────────

@api_view(['GET'])
def summary_view(request):
    debts = Debt.objects.filter(owner=request.user)
    total_gave = debts.filter(debt_type='gave', status='active').aggregate(s=Sum('amount'))['s'] or 0
    total_took = debts.filter(debt_type='took', status='active').aggregate(s=Sum('amount'))['s'] or 0
    pending_count = Debt.objects.filter(counterpart=request.user, status='pending').count()
    close_req_count = Debt.objects.filter(
        status='close_requested'
    ).filter(Q(owner=request.user) | Q(counterpart=request.user)).exclude(
        close_requested_by=request.user).count()
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    try:
        my_rating = request.user.profile.rating
        my_rating_count = request.user.profile.rating_count
    except Exception:
        my_rating = None
        my_rating_count = 0

    return Response({
        'total_gave': total_gave,
        'total_took': total_took,
        'active_count': debts.filter(status='active').count(),
        'closed_count': debts.filter(status='closed').count(),
        'pending_count': pending_count,
        'close_req_count': close_req_count,
        'unread_count': unread_count,
        'balance': float(total_gave) - float(total_took),
        'my_rating': my_rating,
        'my_rating_count': my_rating_count,
    })


@api_view(['GET'])
def history_view(request):
    debts = Debt.objects.filter(owner=request.user, status='closed')
    return Response(DebtSerializer(debts, many=True).data)
