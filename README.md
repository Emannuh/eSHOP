# Duka — Kenyan E-Commerce Store

A full-featured Django 5 e-commerce platform with M-Pesa (Daraja STK Push) payments,
built for Kenyan merchants. Mobile-first, HTMX-powered, no SPA required.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, Django 5.1 |
| Database | PostgreSQL (SQLite for local dev) |
| Frontend | Django templates, Tailwind CSS, HTMX |
| Async | Celery + Redis |
| Payments | Safaricom Daraja API (M-Pesa STK Push) |
| Server | Gunicorn + Nginx |
| Container | Docker + docker-compose |
| CI | GitHub Actions |

---

## Local Setup

### Prerequisites

- Python 3.12+
- Git

### 1. Clone and set up virtual environment

```bash
git clone <repo-url> duka
cd duka
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements/local.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY
```

### 3. Run migrations and seed data

```bash
python manage.py migrate
python manage.py seed
python manage.py createsuperuser
```

### 4. Start the dev server

```bash
python manage.py runserver
```

Open http://localhost:8000 in your browser.
Admin: http://localhost:8000/admin/

---

## Getting Daraja Sandbox Credentials

1. Register at [developer.safaricom.co.ke](https://developer.safaricom.co.ke)
2. Create a new app — tick **Lipa Na Mpesa Sandbox**
3. Copy **Consumer Key** and **Consumer Secret** into `.env`
4. The default sandbox shortcode is `174379` and passkey is provided in the developer portal under **Test Credentials**

---

## Exposing the Callback Locally (ngrok / cloudflared)

Safaricom needs to reach your callback URL over HTTPS. Use a tunnel:

### ngrok

```bash
# Install: https://ngrok.com/download
ngrok http 8000
# Copy the https URL, e.g. https://abc123.ngrok.io
```

### cloudflared (free, no account needed for dev)

```bash
# Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
cloudflared tunnel --url http://localhost:8000
```

Set in `.env`:

```
DARAJA_CALLBACK_URL=https://abc123.ngrok.io/payments/callback/
```

---

## Running with Docker (full stack)

```bash
# Start all services (web, db, redis, celery, nginx)
docker-compose up --build

# Run seed
docker-compose exec web python manage.py seed

# Create superuser
docker-compose exec web python manage.py createsuperuser
```

Services:
- App: http://localhost (port 80 via nginx)
- Direct Gunicorn: http://localhost:8000

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Production Go-Live Checklist

### Safaricom / M-Pesa

- [ ] Apply for a **Paybill** or **Till** number at any Safaricom shop or via the [Business Portal](https://www.safaricom.co.ke/business/mpesa/lipa-na-mpesa)
- [ ] Once approved, log in to the Daraja portal and create a **Production app**
- [ ] Get production **Consumer Key** and **Consumer Secret**
- [ ] Get your **Passkey** from the Daraja production portal
- [ ] Set `DARAJA_ENV=production` in your production `.env`
- [ ] Register your **HTTPS callback URL** with Safaricom: `https://yourdomain.com/payments/callback/`
  - Must be publicly accessible over HTTPS
  - Must not require authentication
- [ ] Test end-to-end with a small real transaction before going live
- [ ] Keep `DARAJA_TRANSACTION_TYPE=CustomerPayBillOnline` for Paybill, or `CustomerBuyGoodsOnline` for Till

### Infrastructure

- [ ] Set a strong `SECRET_KEY` (use `python -c "import secrets; print(secrets.token_urlsafe(50))"`)
- [ ] Set `DEBUG=False`
- [ ] Set `ALLOWED_HOSTS=yourdomain.com`
- [ ] Configure PostgreSQL (`DATABASE_URL=postgres://user:pass@host:5432/duka`)
- [ ] Configure Redis (`REDIS_URL=redis://redis:6379/0`)
- [ ] Provision SSL certificate (Let's Encrypt via Certbot is free)
- [ ] Set `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`
- [ ] Configure production email (SendGrid, SES, etc.)
- [ ] Configure Africa's Talking for live SMS (set `SMS_BACKEND=apps.notifications.backends.africastalking.AfricasTalkingBackend`)
- [ ] Set up a media storage bucket (AWS S3 or compatible) for production images
- [ ] Set up log aggregation (Sentry, CloudWatch, etc.)
- [ ] Set up health monitoring and uptime alerts
- [ ] Run `python manage.py check --deploy` and fix all warnings

### Before Launch

- [ ] Run `python manage.py seed` (or import your real product catalog)
- [ ] Test the full checkout flow end-to-end with real M-Pesa
- [ ] Verify the callback receives and processes payments
- [ ] Set up Celery Beat to run `check_pending_payments` every 2 minutes
- [ ] Configure database backups
