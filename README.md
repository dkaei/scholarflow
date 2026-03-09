# ScholarFlow

ScholarFlow is a Django-based e-learning platform for students and teachers.

## Features
- User authentication and profile pages
- Course creation and enrolment workflow
- Lesson-based course structure
- Material upload and inline preview (video, image, PDF, etc.)
- Study room chat
- Notifications
- User search for teachers
- Course visibility controls

## Tech stack
- Python 3.10
- Django 4.2
- SQLite (development)
- Django Channels / ASGI for real-time study room chat
- Pillow for image uploads

## Setup
1. Create and activate a virtual environment
2. Install dependencies
3. Run migrations
4. Start the server

(bash)
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

## Unit testing
(bash) python manage.py test

## Default URL
http://127.0.0.1:8000/

## Accounts
Admin: (bash) python manage.py createsuperuser
Teacher: Create on frontend or via admin
Student: Create on frontend or via admin