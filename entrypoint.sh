#!/bin/sh
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser --noinput --username=admin --email=admin@example.com
python manage.py shell -c "from django.contrib.auth.models import User; user = User.objects.get(username='admin'); user.set_password('admin'); user.save()"
python manage.py runserver 0.0.0.0:8000