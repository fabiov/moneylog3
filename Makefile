setup:
	pip install -r requirements.txt

run:
	. venv/bin/activate && python3 manage.py runserver
venv:
	source venv/bin/activate
