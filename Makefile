setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt
	. .venv/bin/activate && python3 manage.py migrate
	. .venv/bin/activate && python3 manage.py collectstatic --noinput

run:
# 	docker compose up -d
	. .venv/bin/activate && python3 manage.py runserver

gunicorn:
	. .venv/bin/activate && gunicorn core.wsgi:application --bind 0.0.0.0:8000

venv:
	source .venv/bin/activate

# python manage.py createsuperuser
# python manage.py copy_data