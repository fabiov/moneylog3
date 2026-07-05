from django.core.management.base import BaseCommand
from django.db import connections
from datetime import datetime

class Command(BaseCommand):
    help = 'Copies data from source_db to destination_db record by record with autocommit'

    def handle(self, *args, **options):
        source_conn = connections['moneylog2']
        dest_conn = connections['default']

        now = datetime.now()

        # Enable autocommit for the destination to avoid transaction overhead
        dest_conn.autocommit = True
        try:
            with source_conn.cursor() as src_cursor, dest_conn.cursor() as dest_cursor:

                # DELETE ALL DATA
                dest_cursor.execute("DELETE FROM provisions")
                dest_cursor.execute("DELETE FROM movements")
                dest_cursor.execute("DELETE FROM accounts")
                dest_cursor.execute("DELETE FROM categories")

                # 1. Process "accounts" table
                src_cursor.execute("SELECT id, name, status, user_id, created_at, updated_at FROM accounts")
                insert_account_query = (
                    "INSERT INTO accounts (id, name, status, user_id, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s)"
                )
                accounts_data = src_cursor.fetchall()

                for row in accounts_data:
                    dest_cursor.execute(insert_account_query, [row[0], row[1], row[2], row[3], now, now])

                # 2. Process "categories" table
                src_cursor.execute("SELECT id, name, active, user_id, created_at, updated_at FROM categories")
                insert_categories_query = (
                    "INSERT INTO categories (id, name, active, user_id, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s)"
                )
                categories_data = src_cursor.fetchall()
                for row in categories_data:
                    dest_cursor.execute(insert_categories_query, [row[0], row[1], row[2], row[3], now, now])

                # 3. Process "movements" table
                src_cursor.execute("SELECT account_id, category_id, date, amount, description FROM movements")
                insert_movements_query = (
                    "INSERT INTO movements (account_id, category_id, date, amount, description, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
                )
                movements_data = src_cursor.fetchall()
                for row in movements_data:
                    dest_cursor.execute(insert_movements_query, [row[0], row[1], row[2], row[3], row[4], now, now])

                # 4. Process "provisions" table
                src_cursor.execute("SELECT user_id, date, amount, description, created_at FROM provisions")
                insert_provisions_query = (
                    "INSERT INTO provisions (user_id, date, amount, description, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s)"
                )
                provisions_data = src_cursor.fetchall()
                for row in provisions_data:
                    dest_cursor.execute(insert_provisions_query, [row[0], row[1], row[2], row[3], row[4], now])

            self.stdout.write(self.style.SUCCESS('Entrambe le tabelle sono state sincronizzate correttamente.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Errore durante la sincronizzazione: {e}'))

        finally:
            # Reset autocommit to default if necessary
            dest_conn.autocommit = False