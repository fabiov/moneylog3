setup:
	pip install -r requirements.txt
	python manage.py migrate

run:
	docker compose up -d
	. venv/bin/activate && python3 manage.py runserver

venv:
	source venv/bin/activate

# python manage.py createsuperuser
# python manage.py copy_data