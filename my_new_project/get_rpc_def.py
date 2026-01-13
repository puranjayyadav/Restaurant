from django.db import connection
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_new_project.settings')
django.setup()

def get_rpc_definition():
    with connection.cursor() as cursor:
        cursor.execute("SELECT prosrc FROM pg_proc WHERE proname = 'match_lemon8_articles'")
        row = cursor.fetchone()
        if row:
            print(row[0])
        else:
            print("RPC not found")

if __name__ == "__main__":
    get_rpc_definition()
