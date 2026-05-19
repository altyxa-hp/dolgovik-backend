from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    path('auth/register/',              views.RegisterView.as_view()),
    path('auth/login/',                 TokenObtainPairView.as_view()),
    path('auth/refresh/',               TokenRefreshView.as_view()),
    path('auth/me/',                    views.me_view),

    # Проверка пользователя по email
    path('users/check/',                views.check_user),

    # Уведомления
    path('notifications/',              views.notifications_view),
    path('notifications/read-all/',     views.mark_all_read),
    path('notifications/<int:pk>/read/', views.mark_read),

    # Долги
    path('debts/',                      views.DebtListCreateView.as_view()),
    path('debts/incoming/',             views.incoming_requests),
    path('debts/close-requests/',       views.close_requests),
    path('debts/history/',              views.history_view),
    path('debts/<uuid:pk>/',            views.DebtDetailView.as_view()),
    path('debts/<uuid:pk>/approve/',    views.approve_debt),
    path('debts/<uuid:pk>/reject/',     views.reject_debt),
    path('debts/<uuid:pk>/close/',      views.request_close),

    path('public/debt/<uuid:token>/',   views.public_debt_view),
    path('summary/',                    views.summary_view),
]
