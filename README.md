# CodeAlpha Restaurant Management System

A Django REST Framework backend for restaurant operations, developed as Task 3 of the CodeAlpha Backend Development Internship.

## Features

- Menu item management and category filtering
- Restaurant table management
- Table reservations with validation
- Customer order creation and order status tracking
- Inventory and ingredient recipe management
- Automatic inventory deduction when an order is confirmed
- Low-stock reporting
- Daily sales reporting
- Django Admin interface
- Automated API tests

## Technology Stack

- Python
- Django
- Django REST Framework
- SQLite for local development
- PostgreSQL for production deployment
- django-filter
- Django Admin

## Project Structure

```text
CodeAlpha_RestaurantManagement/
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── restaurant/
│   ├── migrations/
│   ├── admin.py
│   ├── models.py
│   ├── permissions.py
│   ├── serializers.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── manage.py
├── requirements.txt
└── README.md
```

## Local Installation

### 1. Clone the repository

```bash
git clone https://github.com/shivamsahu0108/CodeAlpha_RestaurantManagement.git
cd CodeAlpha_RestaurantManagement
```

### 2. Create and activate a virtual environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Apply database migrations

```bash
python manage.py migrate
```

### 5. Create an administrator

```bash
python manage.py createsuperuser
```

### 6. Start the development server

```bash
python manage.py runserver
```

Open the API at `http://127.0.0.1:8000/api/` and the administration panel at `http://127.0.0.1:8000/admin/`.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET, POST | `/api/menu/` | List or create menu items |
| GET, POST | `/api/tables/` | List or create tables |
| GET, POST | `/api/reservations/` | List or create reservations |
| POST | `/api/reservations/{id}/cancel/` | Cancel a reservation |
| GET, POST | `/api/inventory/` | List or create inventory items |
| GET | `/api/inventory/low_stock/` | Retrieve low-stock items |
| GET, POST | `/api/recipes/` | List or create ingredient recipes |
| GET, POST | `/api/orders/` | List or create orders |
| PATCH | `/api/orders/{id}/` | Update order status |
| GET | `/api/reports/daily-sales/` | View daily sales summary |

Staff permissions apply to operational endpoints as configured in the application.

## Run Tests

```bash
python manage.py check
python manage.py test restaurant
```

## Environment Configuration

Production deployments should use environment variables for the Django secret key, database credentials, debug setting, and allowed hosts. Never commit production secrets to GitHub.

## Live Demo

- API Base URL: Add your deployed API URL after deployment.
- Admin Panel: Add your deployed admin URL after deployment.
- GitHub Repository: https://github.com/shivamsahu0108/CodeAlpha_RestaurantManagement

## Internship Project

Developed for the CodeAlpha Backend Development Internship.

## License

This project is intended for educational and portfolio purposes.