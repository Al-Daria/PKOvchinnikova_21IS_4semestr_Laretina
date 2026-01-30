import psycopg2
from psycopg2 import sql, OperationalError
from datetime import datetime
from pathlib import Path
import os


class DatabaseManager:
    """Управление базой данных портфолио"""

    # Конфигурация базы данных
    DB_CONFIG = {
        'dbname': 'research_portfolio',
        'user': 'postgres',
        'password': '1111',
        'host': 'localhost',
        'port': '5432'
    }

    # Типы записей
    ENTRY_TYPES = ['Публикация', 'Конференция', 'Грант', 'Преподавание', 'Достижение']

    def __init__(self):
        self.connection = None
        self.connect()
        self.ensure_tables_exist()

    def connect(self):
        """Подключение к базе данных"""
        try:
            self.connection = psycopg2.connect(**self.DB_CONFIG)
            print("✓ Подключение к БД успешно")
            return True
        except OperationalError as e:
            print(f"✗ Ошибка подключения: {e}")
            return False

    def ensure_tables_exist(self):
        """Проверка и создание таблиц"""
        try:
            cursor = self.connection.cursor()

            # Проверяем существование таблицы entries
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'entries'
                )
            """)

            if not cursor.fetchone()[0]:
                print("Создание таблиц...")
                self.create_tables()
            else:
                print("✓ Таблицы существуют")

            cursor.close()
            return True

        except Exception as e:
            print(f"Ошибка проверки таблиц: {e}")
            return False

    def create_tables(self):
        """Создание всех таблиц"""
        try:
            cursor = self.connection.cursor()

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

            cursor.execute("""
                CREATE TABLE coauthors (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE
                )
            """)

            cursor.execute("""
                CREATE TABLE entry_coauthors (
                    entry_id INTEGER REFERENCES entries(id) ON DELETE CASCADE,
                    coauthor_id INTEGER REFERENCES coauthors(id) ON DELETE CASCADE,
                    PRIMARY KEY (entry_id, coauthor_id)
                )
            """)

            cursor.execute("""
                CREATE TABLE activity_log (
                    id SERIAL PRIMARY KEY,
                    date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    description TEXT NOT NULL,
                    entry_id INTEGER REFERENCES entries(id) ON DELETE CASCADE
                )
            """)

            # Индексы для оптимизации
            cursor.execute("CREATE INDEX idx_entries_type ON entries(entry_type)")
            cursor.execute("CREATE INDEX idx_entries_year ON entries(year)")
            cursor.execute("CREATE INDEX idx_entries_created ON entries(created_at)")
            cursor.execute("CREATE INDEX idx_activity_date ON activity_log(date)")

            self.connection.commit()
            cursor.close()
            print("✓ Все таблицы созданы")

        except Exception as e:
            self.connection.rollback()
            raise

    def get_entries(self, sort_by="created_at", sort_order="DESC"):
        """Получение всех записей с сортировкой"""
        try:
            cursor = self.connection.cursor()
            query = sql.SQL("""
                SELECT id, title, entry_type, year, 
                       TO_CHAR(created_at, 'DD.MM.YYYY HH24:MI') as created_at,
                       file_path
                FROM entries
                ORDER BY {sort_by} {sort_order}
            """).format(
                sort_by=sql.Identifier(sort_by),
                sort_order=sql.SQL(sort_order)
            )

            cursor.execute(query)
            entries = cursor.fetchall()
            cursor.close()
            return entries

        except Exception as e:
            print(f"Ошибка получения записей: {e}")
            return []

    def create_entry(self, title, entry_type, year, file_path):
        """Создание новой записи"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO entries (title, entry_type, year, file_path)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (title, entry_type, year, file_path))

            entry_id = cursor.fetchone()[0]

            # Логируем действие
            cursor.execute("""
                INSERT INTO activity_log (description, entry_id)
                VALUES (%s, %s)
            """, (f"Создана запись: '{title}'", entry_id))

            self.connection.commit()
            cursor.close()
            return entry_id

        except Exception as e:
            self.connection.rollback()
            raise

    def update_entry(self, entry_id, title, entry_type, year):
        """Обновление записи"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE entries 
                SET title = %s, entry_type = %s, year = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (title, entry_type, year, entry_id))

            cursor.execute("""
                INSERT INTO activity_log (description, entry_id)
                VALUES (%s, %s)
            """, (f"Обновлена запись: '{title}'", entry_id))

            self.connection.commit()
            cursor.close()
            return True

        except Exception as e:
            self.connection.rollback()
            raise

    def delete_entry(self, entry_id):
        """Удаление записи"""
        try:
            cursor = self.connection.cursor()

            cursor.execute("SELECT title FROM entries WHERE id = %s", (entry_id,))
            title = cursor.fetchone()[0]

            cursor.execute("DELETE FROM entries WHERE id = %s", (entry_id,))

            cursor.execute("""
                INSERT INTO activity_log (description)
                VALUES (%s)
            """, (f"Удалена запись: '{title}'",))

            self.connection.commit()
            cursor.close()
            return True

        except Exception as e:
            self.connection.rollback()
            raise

    def get_coauthors(self, entry_id):
        """Получение соавторов записи"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT c.name 
                FROM coauthors c
                JOIN entry_coauthors ec ON c.id = ec.coauthor_id
                WHERE ec.entry_id = %s
                ORDER BY c.name
            """, (entry_id,))

            coauthors = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return coauthors

        except Exception as e:
            print(f"Ошибка получения соавторов: {e}")
            return []

    def add_coauthor(self, entry_id, coauthor_name):
        """Добавление соавтора"""
        try:
            cursor = self.connection.cursor()

            cursor.execute("SELECT id FROM coauthors WHERE name = %s", (coauthor_name,))
            result = cursor.fetchone()

            if result:
                coauthor_id = result[0]
            else:
                cursor.execute("INSERT INTO coauthors (name) VALUES (%s) RETURNING id", (coauthor_name,))
                coauthor_id = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO entry_coauthors (entry_id, coauthor_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (entry_id, coauthor_id))

            cursor.execute("""
                INSERT INTO activity_log (description, entry_id)
                VALUES (%s, %s)
            """, (f"Добавлен соавтор: '{coauthor_name}'", entry_id))

            self.connection.commit()
            cursor.close()
            return True

        except Exception as e:
            self.connection.rollback()
            raise

    def remove_coauthor(self, entry_id, coauthor_name):
        """Удаление соавтора"""
        try:
            cursor = self.connection.cursor()

            cursor.execute("SELECT id FROM coauthors WHERE name = %s", (coauthor_name,))
            result = cursor.fetchone()

            if result:
                coauthor_id = result[0]
                cursor.execute("""
                    DELETE FROM entry_coauthors 
                    WHERE entry_id = %s AND coauthor_id = %s
                """, (entry_id, coauthor_id))

                cursor.execute("""
                    INSERT INTO activity_log (description, entry_id)
                    VALUES (%s, %s)
                """, (f"Удален соавтор: '{coauthor_name}'", entry_id))

            self.connection.commit()
            cursor.close()
            return True

        except Exception as e:
            self.connection.rollback()
            raise

    def get_statistics(self):
        """Получение статистики для отчетов"""
        stats = {
            'type_distribution': {},
            'year_distribution': {},
            'unique_coauthors': 0,
            'total_entries': 0,
            'recent_entries': []
        }

        try:
            cursor = self.connection.cursor()

            # Распределение по типам
            cursor.execute("""
                SELECT entry_type, COUNT(*) 
                FROM entries 
                GROUP BY entry_type 
                ORDER BY COUNT(*) DESC
            """)
            stats['type_distribution'] = dict(cursor.fetchall())

            # Распределение по годам
            cursor.execute("""
                SELECT year, COUNT(*) 
                FROM entries 
                WHERE year IS NOT NULL
                GROUP BY year 
                ORDER BY year
            """)
            stats['year_distribution'] = dict(cursor.fetchall())

            # Уникальные соавторы
            cursor.execute("SELECT COUNT(DISTINCT name) FROM coauthors")
            stats['unique_coauthors'] = cursor.fetchone()[0] or 0

            # Общее количество записей
            cursor.execute("SELECT COUNT(*) FROM entries")
            stats['total_entries'] = cursor.fetchone()[0] or 0

            # Последние 5 записей
            cursor.execute("""
                SELECT title, entry_type, year, 
                       TO_CHAR(created_at, 'DD.MM.YYYY') as created_date
                FROM entries
                ORDER BY created_at DESC
                LIMIT 5
            """)
            stats['recent_entries'] = cursor.fetchall()

            cursor.close()

        except Exception as e:
            print(f"Ошибка получения статистики: {e}")

        return stats

    def close(self):
        """Закрытие соединения"""
        if self.connection:
            self.connection.close()