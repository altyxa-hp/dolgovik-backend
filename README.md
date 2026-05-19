# Долговик — Django Backend

## Структура проекта

```
dolgovik_backend/
├── manage.py
├── requirements.txt
├── .env.example          ← скопируй как .env
├── dolgovik_backend/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── api/
    ├── models.py         ← модели: Debt, UserProfile, DebtActivity
    ├── serializers.py    ← преобразование данных
    ├── views.py          ← логика API
    ├── urls.py           ← маршруты
    └── admin.py          ← панель администратора
```

## Установка (шаг за шагом)

### 1. Установи Python и PostgreSQL
- Python 3.11+: https://python.org
- PostgreSQL: https://postgresql.org

### 2. Создай базу данных
```sql
-- Открой pgAdmin или psql и выполни:
CREATE DATABASE dolgovik_db;
```

### 3. Установи зависимости
```bash
cd dolgovik_backend
pip install -r requirements.txt
```

### 4. Настрой переменные окружения
```bash
cp .env.example .env
# Открой .env и поставь свой пароль от PostgreSQL
```

### 5. Примени миграции (создай таблицы в БД)
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Создай администратора
```bash
python manage.py createsuperuser
```

### 7. Запусти сервер
```bash
python manage.py runserver
```

Сервер запустится на: http://127.0.0.1:8000

## API эндпоинты

| Метод | URL | Описание | Авторизация |
|-------|-----|----------|-------------|
| POST | /api/auth/register/ | Регистрация | Нет |
| POST | /api/auth/login/ | Вход (получить токен) | Нет |
| POST | /api/auth/refresh/ | Обновить токен | Нет |
| GET | /api/auth/me/ | Данные профиля | Да |
| GET | /api/debts/ | Список долгов | Да |
| POST | /api/debts/ | Создать долг | Да |
| GET | /api/debts/<id>/ | Один долг | Да |
| PATCH | /api/debts/<id>/ | Изменить долг | Да |
| DELETE | /api/debts/<id>/ | Удалить долг | Да |
| POST | /api/debts/<id>/close/ | Закрыть долг | Да |
| POST | /api/debts/<id>/remind/ | Напомнить должнику | Да |
| GET | /api/public/debt/<token>/ | Публичная ссылка | Нет |
| GET | /api/summary/ | Статистика | Да |

## Примеры запросов

### Регистрация
```json
POST /api/auth/register/
{
  "email": "user@example.com",
  "first_name": "Айбек",
  "last_name": "Токтосунов",
  "password": "mypassword123",
  "password2": "mypassword123"
}
```

### Создать долг
```json
POST /api/debts/
Authorization: Bearer <твой_токен>
{
  "debt_type": "gave",
  "person_name": "Алмаз Курбанов",
  "person_email": "almaz@example.com",
  "amount": "25000.00",
  "currency": "KGS",
  "note": "На покупку телефона",
  "due_date": "2026-06-01"
}
```

### Фильтр долгов
```
GET /api/debts/?type=gave&status=active
```

## Фильтры для списка долгов
- `?type=gave` — только "дал в долг"
- `?type=took` — только "взял в долг"
- `?status=active` — только активные
- `?status=closed` — только закрытые

## Панель администратора
http://127.0.0.1:8000/admin/
(войди с данными createsuperuser)
