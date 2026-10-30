# MoneyLog 3

MoneyLog is a personal finance application written in Python with Django. Its
interface is built on Django Admin, customized with
[Django Unfold](https://unfoldadmin.com/), rather than a separate frontend or REST
API. The UI is in Italian, displays amounts in euros, and uses the `Europe/Rome`
time zone.

## Features

- Manage accounts with open, closed, and main statuses, and organize movements
  by category. Positive amounts represent income; negative amounts represent expenses.
- Transfer funds between accounts using linked debit and credit movements.
  Editing the amount or date through the admin synchronizes the paired movement;
  deleting a transfer movement through the admin also deletes its counterpart.
- Search movements and filter by date, amount, category, and account.
- View account balances, spendable funds, monthly income and expenses, a six-month
  cash-flow trend, and a 24-month balance trend on the dashboard.
- Track planned provisions (`Accantonamenti`) and configure personal preferences
  for payday, the averaging window, and provisioning statistics.
- Use a web app manifest and service worker for home-screen installation and
  cached pages/assets. This is not a full offline transaction-entry workflow.

Financial admin lists and dashboard calculations are scoped to the logged-in user.

## Project structure

```text
.
|-- core/                       Django project configuration
|   |-- settings.py             Apps, databases, localization, static files, Unfold
|   |-- urls.py                 Admin, home redirect, manifest, and service worker
|   |-- asgi.py                 ASGI entry point
|   `-- wsgi.py                 WSGI entry point used by Gunicorn
|-- moneylog/                   Main Django application
|   |-- models.py               Accounts, categories, movements, settings, provisions
|   |-- admin.py                User-scoped admin, filters, transfers, balance cards
|   |-- forms.py                Transfer dialog and grouped account selectors
|   |-- dashboard.py            Dashboard aggregations and budget calculations
|   |-- management/commands/
|   |   `-- copy_data.py         Legacy MySQL data import
|   |-- migrations/             Database schema migrations
|   |-- static/                 Icons and favicons
|   |-- tests.py                Transfer, account grouping, and provision admin tests
|   `-- test_dashboard.py       Dashboard tests
|-- templates/                  Django Admin and Unfold template overrides
|   |-- admin/                  Dashboard, branding, forms, and account cards
|   |-- unfold/                 Layout override
|   |-- manifest.json           Web app metadata
|   `-- sw.js                   Service worker
|-- formats/it/formats.py       Italian date/number formatting
|-- manage.py                   Django command-line entry point
|-- requirements.txt            Pinned Python dependencies
|-- Makefile                    Local setup, development, and Gunicorn commands
|-- docker-compose.yml          Optional PostgreSQL service only
|-- server-setup.sh             Host-specific Linux deployment provisioning
|-- pyrightconfig.json          Type-checker configuration with local absolute paths
|-- test_*.py                   Standalone diagnostic scripts
`-- set_pass.py                 Hard-coded local password/privilege helper
```

Requests to `/` redirect to `/admin/`. Django Admin handles the application pages;
`moneylog/views.py` is currently a placeholder. Unfold calls
`moneylog.dashboard.dashboard_callback` to populate the custom dashboard template.
Static files are collected into the generated `staticfiles/` directory and served
with WhiteNoise when running the application directly.

### Data model

| Model | Purpose and relationships |
| --- | --- |
| `Account` | Belongs to a user; holds movements. Saving a main account demotes that user's other main accounts to open. |
| `Category` | Belongs to a user; optionally groups movements and calculates historical averages. |
| `Movement` | A dated decimal amount and description attached to an account, with an optional category and one-to-one link to a transfer counterpart. |
| `Setting` | One record per user containing payday, averaging months, and the provisioning flag. |
| `Provision` | A dated amount and description belonging to a user, representing planned funds set aside. |

## Local development

### Prerequisites

- Python 3.12 or newer, as required by Django 6.0.
- `pip`, virtual environment support, and `make` for the supplied shortcuts.
- Native build tools, Python development headers, MySQL/MariaDB client development
  libraries, and `pkg-config` if `mysqlclient` must be built from source. It is
  installed by `requirements.txt` even when using SQLite.
- Docker Compose only if you choose PostgreSQL; it is not required for SQLite.

Run these commands from the repository root, with `python3` pointing to a
supported Python version:

```bash
make setup
.venv/bin/python manage.py createsuperuser
make run
```

`make setup` creates `.venv`, installs dependencies, applies migrations, and
collects static files. `make run` starts Django's development server.
Open <http://127.0.0.1:8000/admin/> and sign in with the superuser you created.
Start by adding accounts and categories, then record movements or use
**Nuovo Giroconto** to transfer funds. Preferences are available under
**Preferenze**.

For manual management commands, either use `.venv/bin/python` directly or activate
the environment with `source .venv/bin/activate` in your current shell.
Use Django's `changepassword` command for password changes rather than `set_pass.py`,
which targets a hard-coded user and also grants staff/superuser privileges.

### Database configuration

Database connections are configured directly in `core/settings.py`; there is no
environment-variable or `.env` loader.

| Connection | Default role |
| --- | --- |
| `default` | SQLite database at `db.sqlite3` in the repository root. |
| `moneylog2` | Legacy MySQL source used by `copy_data`; not needed for normal SQLite usage. |

For PostgreSQL, start the supplied PostgreSQL 16 container:

```bash
docker compose up -d db
```

Then replace the SQLite `default` entry in `core/settings.py` with the commented
PostgreSQL configuration, review its connection values against
`docker-compose.yml`, and run `.venv/bin/python manage.py migrate`.
The container exposes port 5432 and persists data in the `postgres_data` named
volume. Switching database configuration does not copy existing SQLite data.

## Tests

Run the application test modules explicitly:

```bash
.venv/bin/python manage.py test moneylog.tests moneylog.test_dashboard
```

These cover transfer validation and synchronization, grouped account choices,
provision admin defaults, and dashboard calculations. The root-level `test_*.py`
files are diagnostic scripts, not an isolated test suite; several query existing
users and data at import time. Avoid unqualified test discovery when you only
intend to run the application tests.

`pyrightconfig.json` contains machine-specific paths; adjust them to your local
environment before using Pyright.

## Importing legacy MoneyLog data

The `copy_data` management command reads accounts, categories, movements, and
provisions from the `moneylog2` MySQL connection into `default`.

**Warning:** it deletes all destination rows in those four tables before copying.
The operation uses autocommit, so a failure can leave the destination partially
populated. Back up the destination and review the command before running it.

Configure both connections and apply destination migrations first. Destination
Django users must already exist with IDs matching the source records: the command
does not import users or settings, and it does not preserve transfer links.

```bash
.venv/bin/python manage.py copy_data
```

## Deployment notes

`make gunicorn` serves `core.wsgi:application` on `0.0.0.0:8000` using `.venv`.
Run migrations and `collectstatic` as part of deployment.

The checked-in settings are for development: `DEBUG` is enabled, all hosts are
allowed, and the secret key and database connection values are hard-coded.
Configure production secrets, allowed hosts, HTTPS, and `DEBUG = False` before
exposing the application publicly.

`server-setup.sh` is a host-specific, privileged Debian/Ubuntu provisioning script,
not a generic deployment command. It changes swap, packages, firewall rules,
Nginx, a Gunicorn systemd service, and Certbot configuration. Review its hard-coded
domain, paths, certificate assumptions, and SSH firewall access before use.
It expects application files at `/var/www/moneylog3`, uses `venv` rather than the
Makefile's `.venv`, and does not apply database migrations or create an admin user.
