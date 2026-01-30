import psycopg2
from psycopg2 import OperationalError
import sys


def create_database():
    """Создание БД и таблиц"""
    print("=" * 50)
    print("Создание базы данных 'research_portfolio'")
    print("=" * 50)

    conn = None
    cursor = None

    try:
        # Подключаемся к postgres
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password="1111",
            host="localhost",
            port="5432"
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # Проверяем существование БД
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'research_portfolio'")
        exists = cursor.fetchone()

        if exists:
            print("База данных уже существует.")
            response = input("Пересоздать? (y/n): ")
            if response.lower() == 'y':
                cursor.execute("DROP DATABASE research_portfolio")
                print("Старая БД удалена.")
            else:
                print("Используем существующую БД.")

        # Создаем БД
        cursor.execute("CREATE DATABASE research_portfolio")
        print("БД создана.")

        cursor.close()
        conn.close()

        # Подключаемся к новой БД
        conn = psycopg2.connect(
            dbname="research_portfolio",
            user="postgres",
            password="1111",
            host="localhost",
            port="5432"
        )
        cursor = conn.cursor()

        # Создаем таблицы
        print("\nСоздание таблиц...")

        cursor.execute("""
            CREATE TABLE entries (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                entry_type VARCHAR(100) NOT NULL,
                year INTEGER,
                file_path VARCHAR(500) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ Таблица 'entries'")

        cursor.execute("""
            CREATE TABLE coauthors (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE
            )
        """)
        print("✓ Таблица 'coauthors'")

        cursor.execute("""
            CREATE TABLE entry_coauthors (
                entry_id INTEGER REFERENCES entries(id) ON DELETE CASCADE,
                coauthor_id INTEGER REFERENCES coauthors(id) ON DELETE CASCADE,
                PRIMARY KEY (entry_id, coauthor_id)
            )
        """)
        print("✓ Таблица 'entry_coauthors'")

        cursor.execute("""
            CREATE TABLE activity_log (
                id SERIAL PRIMARY KEY,
                date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                description TEXT NOT NULL,
                entry_id INTEGER REFERENCES entries(id) ON DELETE CASCADE
            )
        """)
        print("✓ Таблица 'activity_log'")

        conn.commit()
        print("\n✓ Все таблицы созданы!")

        # Проверяем
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = cursor.fetchall()
        print(f"\nСоздано таблиц: {len(tables)}")
        for table in tables:
            print(f"  • {table[0]}")

    except OperationalError as e:
        print(f"\n✗ Ошибка подключения: {e}")
        print("\nУбедитесь, что:")
        print("1. PostgreSQL запущен")
        print("2. Пользователь 'postgres' существует")
        print("3. Пароль: 1111")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print("\nСоединение закрыто.")

    print("\n" + "=" * 50)
    print("НАСТРОЙКА ЗАВЕРШЕНА!")
    print("Запустите: python portfolio_app.py")
    print("=" * 50)


if __name__ == "__main__":
    create_database()