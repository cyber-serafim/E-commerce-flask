
import sqlite3

def print_all_data_from_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Получаем список всех таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    if not tables:
        print("В базе данных нет таблиц.")
        return

    for (table_name,) in tables:
        print(f"\nТаблица: {table_name}")
        try:
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]

            # Печатаем заголовки колонок
            print(" | ".join(columns))

            # Печатаем строки данных
            for row in rows:
                print(" | ".join(str(cell) for cell in row))

        except Exception as e:
            print(f"Ошибка при чтении таблицы {table_name}: {e}")

    conn.close()

# Пример использования
print_all_data_from_db("database.sqlite3")
