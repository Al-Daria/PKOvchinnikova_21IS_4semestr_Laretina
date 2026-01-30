"""
Pytest тесты для приложения "Планировщик индивидуального образовательного маршрута"
Без использования tkinter - тестируем только логику
"""
import pytest
import sqlite3
import json
import os
import tempfile
import sys
from datetime import datetime

# ==================== MOCK КЛАССЫ ====================

class MockTk:
    """Mock класс для замены Tkinter окна"""
    def __init__(self):
        pass

    def mainloop(self):
        pass

    def destroy(self):
        pass

    def protocol(self, *args):
        pass

    def winfo_width(self):
        return 1200

    def winfo_height(self):
        return 700

    def winfo_screenwidth(self):
        return 1920

    def winfo_screenheight(self):
        return 1080

    def update_idletasks(self):
        pass

    def geometry(self, *args):
        pass

    def title(self, *args):
        pass

    def iconbitmap(self, *args):
        pass

class MockToplevel:
    """Mock класс для Toplevel окон"""
    def __init__(self, *args, **kwargs):
        pass

    def title(self, *args):
        pass

    def geometry(self, *args):
        pass

    def transient(self, *args):
        pass

    def grab_set(self):
        pass

    def configure(self, *args, **kwargs):
        pass

    def destroy(self):
        pass


class EducationalRoutePlanner:
    """Mock класс для тестирования без tkinter"""
    def __init__(self, root=None):
        self.root = root or MockTk()
        self.db_path = None  # Будет установлено в setup_database
        self.conn = None
        self.cursor = None
        self.setup_database()

    def setup_database(self):
        """Настройка базы данных"""
        # Используем временную БД с явным закрытием файла
        import uuid
        self.db_path = os.path.join(tempfile.gettempdir(), f'test_db_{uuid.uuid4().hex}.db')

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()

        # Создаем таблицы
        self.create_tables()

        # Загружаем компетенции
        self.load_competencies()

        # Загружаем достижения
        self.load_achievements()

    def create_tables(self):
        """Создание таблиц в БД"""
        # Таблица целей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS цели (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                название TEXT NOT NULL,
                тип TEXT NOT NULL,
                статус TEXT NOT NULL,
                план_дата DATE,
                факт_дата DATE,
                описание TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица навыков
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS навыки (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                название TEXT UNIQUE NOT NULL
            )
        ''')

        # Таблица связи целей и навыков
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS цель_навыки (
                цель_id INTEGER,
                навык_id INTEGER,
                FOREIGN KEY (цель_id) REFERENCES цели (id) ON DELETE CASCADE,
                FOREIGN KEY (навык_id) REFERENCES навыки (id) ON DELETE CASCADE,
                PRIMARY KEY (цель_id, навык_id)
            )
        ''')

        # Таблица компетенций
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS компетенции (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                название TEXT NOT NULL,
                категория TEXT NOT NULL,
                описание TEXT
            )
        ''')

        # Таблица связи целей и компетенций
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS цель_компетенции (
                цель_id INTEGER,
                компетенция_id INTEGER,
                уровень INTEGER CHECK (уровень BETWEEN 1 AND 5),
                FOREIGN KEY (цель_id) REFERENCES цели (id) ON DELETE CASCADE,
                FOREIGN KEY (компетенция_id) REFERENCES компетенции (id) ON DELETE CASCADE,
                PRIMARY KEY (цель_id, компетенция_id)
            )
        ''')

        # Таблица достижений
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS достижения (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                код TEXT UNIQUE NOT NULL,
                название TEXT NOT NULL,
                описание TEXT,
                получено BOOLEAN DEFAULT 0,
                дата_получения DATE
            )
        ''')

        # Таблица целей на семестр
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS цели_на_семестр (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                текст_цели TEXT NOT NULL,
                тип_цели TEXT NOT NULL,
                параметр TEXT,
                текущий_прогресс INTEGER DEFAULT 0,
                целевой_прогресс INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    def load_competencies(self):
        """Загрузка компетенций из файла"""
        competencies = [
            {"название": "Работа с БД", "категория": "Технические", "описание": "Умение работать с базами данных"},
            {"название": "Презентация результатов", "категория": "Коммуникативные", "описание": "Умение презентовать результаты работы"},
            {"название": "Управление проектами", "категория": "Организационные", "описание": "Умение управлять проектами"},
            {"название": "Анализ данных", "категория": "Технические", "описание": "Умение анализировать данные"},
            {"название": "Программирование", "категория": "Технические", "описание": "Умение программировать"}
        ]

        for comp in competencies:
            self.cursor.execute(
                "INSERT OR IGNORE INTO компетенции (название, категория, описание) VALUES (?, ?, ?)",
                (comp["название"], comp["категория"], comp.get("описание", ""))
            )

        self.conn.commit()

    def load_achievements(self):
        """Загрузка достижений"""
        achievements = [
            ("старт", "Старт", "Добавлена первая цель", 0, None),
            ("пунктуальный", "Пунктуальный", "3 цели завершены в срок", 0, None),
            ("многоцелевой", "Многоцелевой", "Цели 3 разных типов", 0, None),
            ("навыковый_рост", "Навыковый рост", "4 цели с одним навыком", 0, None),
            ("планировщик", "Планировщик", "5 целей в процессе одновременно", 0, None)
        ]

        for code, name, desc, obtained, date in achievements:
            self.cursor.execute(
                "INSERT OR IGNORE INTO достижения (код, название, описание, получено, дата_получения) VALUES (?, ?, ?, ?, ?)",
                (code, name, desc, obtained, date)
            )

        self.conn.commit()

    def check_achievements(self):
        """Проверка и обновление достижений"""
        # Достижение "Старт" - есть хотя бы одна цель
        self.cursor.execute("SELECT COUNT(*) FROM цели")
        goal_count = self.cursor.fetchone()[0]

        if goal_count > 0:
            self.cursor.execute(
                "UPDATE достижения SET получено = 1, дата_получения = CURRENT_DATE WHERE код = 'старт' AND получено = 0"
            )

        # Достижение "Планировщик" - 5+ целей в процессе
        self.cursor.execute("SELECT COUNT(*) FROM цели WHERE статус = 'В процессе'")
        in_process_count = self.cursor.fetchone()[0]

        if in_process_count >= 5:
            self.cursor.execute(
                "UPDATE достижения SET получено = 1, дата_получения = CURRENT_DATE WHERE код = 'планировщик' AND получено = 0"
            )

        # Достижение "Многоцелевой" - цели 3+ разных типов
        self.cursor.execute("SELECT COUNT(DISTINCT тип) FROM цели WHERE статус = 'Завершено'")
        distinct_types = self.cursor.fetchone()[0]

        if distinct_types >= 3:
            self.cursor.execute(
                "UPDATE достижения SET получено = 1, дата_получения = CURRENT_DATE WHERE код = 'многоцелевой' AND получено = 0"
            )

        # Достижение "Пунктуальный" - 3+ цели завершены в срок (факт_дата <= план_дата)
        self.cursor.execute(
            "SELECT COUNT(*) FROM цели WHERE статус = 'Завершено' AND факт_дата IS NOT NULL AND план_дата IS NOT NULL AND факт_дата <= план_дата"
        )
        on_time_count = self.cursor.fetchone()[0]

        if on_time_count >= 3:
            self.cursor.execute(
                "UPDATE достижения SET получено = 1, дата_получения = CURRENT_DATE WHERE код = 'пунктуальный' AND получено = 0"
            )

        # Достижение "Навыковый рост" - 4+ завершенных цели с одним навыком
        self.cursor.execute('''
            SELECT н.название, COUNT(DISTINCT ц.id) 
            FROM навыки н
            JOIN цель_навыки цн ON н.id = цн.навык_id
            JOIN цели ц ON цн.цель_id = ц.id
            WHERE ц.статус = 'Завершено'
            GROUP BY н.id
            HAVING COUNT(DISTINCT ц.id) >= 4
        ''')
        skill_with_4_goals = self.cursor.fetchone()

        if skill_with_4_goals:
            self.cursor.execute(
                "UPDATE достижения SET получено = 1, дата_получения = CURRENT_DATE WHERE код = 'навыковый_рост' AND получено = 0"
            )

        self.conn.commit()

    def save_goal(self, goal_data):
        """Сохранение цели (упрощенная версия)"""
        try:
            # Валидация обязательных полей
            if not goal_data.get('name') or not goal_data.get('type') or not goal_data.get('status'):
                return False, "Заполните обязательные поля"

            # Валидация даты
            try:
                if goal_data.get('plan_date'):
                    datetime.strptime(goal_data['plan_date'], '%Y-%m-%d')
                if goal_data.get('fact_date'):
                    datetime.strptime(goal_data['fact_date'], '%Y-%m-%d')
            except ValueError:
                return False, "Неверный формат даты. Используйте ГГГГ-ММ-ДД"

            # Сохранение цели
            self.cursor.execute(
                """INSERT INTO цели (название, тип, статус, план_дата, факт_дата, описание) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (goal_data['name'], goal_data['type'], goal_data['status'],
                 goal_data.get('plan_date'), goal_data.get('fact_date'), goal_data.get('description', ''))
            )

            goal_id = self.cursor.lastrowid

            # Сохранение навыков
            skills = goal_data.get('skills', [])
            for skill_name in skills:
                if skill_name:
                    # Добавляем навык, если его нет
                    self.cursor.execute(
                        "INSERT OR IGNORE INTO навыки (название) VALUES (?)",
                        (skill_name,)
                    )

                    # Получаем ID навыка
                    self.cursor.execute("SELECT id FROM навыки WHERE название = ?", (skill_name,))
                    skill_result = self.cursor.fetchone()
                    if skill_result:
                        skill_id = skill_result[0]
                        # Связываем цель с навыком
                        self.cursor.execute(
                            "INSERT OR IGNORE INTO цель_навыки (цель_id, навык_id) VALUES (?, ?)",
                            (goal_id, skill_id)
                        )

            self.conn.commit()
            self.check_achievements()
            return True, "Цель успешно сохранена"

        except Exception as e:
            self.conn.rollback()
            return False, f"Ошибка при сохранении: {str(e)}"

    def refresh_goals_list(self):
        """Обновление списка целей (упрощенная версия)"""
        self.cursor.execute("SELECT id, название, тип, статус, план_дата FROM цели ORDER BY план_дата")
        return self.cursor.fetchall()

    def close(self):
        """Закрытие соединения с БД"""
        try:
            if hasattr(self, 'cursor') and self.cursor:
                self.cursor.close()
        except:
            pass

        try:
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()
        except:
            pass

        # Удаляем файл БД если он существует
        try:
            if hasattr(self, 'db_path') and self.db_path and os.path.exists(self.db_path):
                # Закрываем все возможные соединения
                import gc
                gc.collect()

                # Попробуем удалить файл
                for _ in range(3):  # Попробуем несколько раз
                    try:
                        os.unlink(self.db_path)
                        break
                    except (PermissionError, OSError):
                        import time
                        time.sleep(0.1)  # Небольшая задержка
        except:
            pass


# ==================== ФИКСТУРЫ ====================

@pytest.fixture(scope="function")
def app_instance():
    """Создание экземпляра приложения для тестирования"""
    # Создаем mock-окно для tkinter
    mock_root = MockTk()
    app = EducationalRoutePlanner(mock_root)
    yield app
    app.close()


# ==================== ТЕСТЫ БАЗЫ ДАННЫХ ====================

class TestDatabaseOperations:
    """Тесты операций с базой данных"""

    def test_create_tables(self, app_instance):
        """Тест создания таблиц в БД"""
        # Проверяем, что таблицы созданы
        tables = [
            'цели', 'навыки', 'цель_навыки',
            'компетенции', 'достижения', 'цели_на_семестр'
        ]

        for table in tables:
            app_instance.cursor.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
            )
            result = app_instance.cursor.fetchone()
            assert result is not None, f"Таблица '{table}' не создана"
            assert result[0] == table, f"Неправильное имя таблицы: {result[0]}"

    def test_load_competencies(self, app_instance):
        """Тест загрузки компетенций"""
        # Проверяем, что компетенции загружены
        app_instance.cursor.execute("SELECT COUNT(*) FROM компетенции")
        count = app_instance.cursor.fetchone()[0]
        assert count == 5, f"Ожидалось 5 компетенций, получено {count}"

        # Проверяем конкретные компетенции
        app_instance.cursor.execute("SELECT название FROM компетенции WHERE категория = 'Технические'")
        tech_competencies = [row[0] for row in app_instance.cursor.fetchall()]
        assert "Работа с БД" in tech_competencies, "Компетенция 'Работа с БД' не найдена"
        assert "Программирование" in tech_competencies, "Компетенция 'Программирование' не найдена"

    def test_load_achievements(self, app_instance):
        """Тест загрузки достижений"""
        app_instance.cursor.execute("SELECT COUNT(*) FROM достижения")
        count = app_instance.cursor.fetchone()[0]
        assert count == 5, f"Ожидалось 5 достижений, получено {count}"

        # Проверяем конкретные достижения
        expected_achievements = ['старт', 'пунктуальный', 'многоцелевой', 'навыковый_рост', 'планировщик']
        for achievement in expected_achievements:
            app_instance.cursor.execute("SELECT 1 FROM достижения WHERE код = ?", (achievement,))
            result = app_instance.cursor.fetchone()
            assert result is not None, f"Достижение '{achievement}' не найдено"


# ==================== ТЕСТЫ ОПЕРАЦИЙ С ЦЕЛЯМИ ====================

class TestGoalOperations:
    """Тесты операций с целями"""

    def test_save_goal_valid(self, app_instance):
        """Тест сохранения цели с валидными данными"""
        goal_data = {
            'name': 'Изучить Python',
            'type': 'Курс',
            'status': 'В процессе',
            'plan_date': '2024-12-31',
            'fact_date': '',
            'description': 'Пройти курс по Python',
            'skills': ['Python', 'Программирование']
        }

        success, message = app_instance.save_goal(goal_data)
        assert success, f"Цель не сохранена: {message}"

        # Проверяем, что цель сохранена в БД
        app_instance.cursor.execute("SELECT название FROM цели WHERE название = ?", (goal_data['name'],))
        result = app_instance.cursor.fetchone()
        assert result is not None, "Цель не сохранена в БД"
        assert result[0] == goal_data['name'], f"Неправильное название цели: {result[0]}"

        # Проверяем, что навыки сохранены
        for skill in goal_data['skills']:
            app_instance.cursor.execute("SELECT 1 FROM навыки WHERE название = ?", (skill,))
            skill_result = app_instance.cursor.fetchone()
            assert skill_result is not None, f"Навык '{skill}' не сохранен"

    def test_save_goal_missing_required_fields(self, app_instance):
        """Тест сохранения цели без обязательных полей"""
        # Тест 1: Нет названия
        goal_data = {
            'name': '',
            'type': 'Курс',
            'status': 'В процессе',
            'plan_date': '2024-12-31'
        }

        success, message = app_instance.save_goal(goal_data)
        assert not success, "Цель должна быть отклонена из-за отсутствия названия"
        assert "обязательные" in message.lower() or "заполните" in message.lower()

        # Тест 2: Нет типа
        goal_data = {
            'name': 'Тестовая цель',
            'type': '',
            'status': 'В процессе',
            'plan_date': '2024-12-31'
        }

        success, message = app_instance.save_goal(goal_data)
        assert not success, "Цель должна быть отклонена из-за отсутствия типа"

        # Тест 3: Нет статуса
        goal_data = {
            'name': 'Тестовая цель',
            'type': 'Курс',
            'status': '',
            'plan_date': '2024-12-31'
        }

        success, message = app_instance.save_goal(goal_data)
        assert not success, "Цель должна быть отклонена из-за отсутствия статуса"

    def test_save_goal_invalid_date_format(self, app_instance):
        """Тест сохранения цели с неверным форматом даты"""
        # Неверный формат плановой даты
        goal_data = {
            'name': 'Тестовая цель',
            'type': 'Курс',
            'status': 'В процессе',
            'plan_date': '31-12-2024',  # Неверный формат
            'fact_date': '2024-12-25'    # Правильный формат
        }

        success, message = app_instance.save_goal(goal_data)
        assert not success, "Цель должна быть отклонена из-за неверного формата даты"
        assert "формат даты" in message.lower() or "дата" in message.lower()

        # Неверный формат фактической даты
        goal_data = {
            'name': 'Тестовая цель',
            'type': 'Курс',
            'status': 'Завершено',
            'plan_date': '2024-12-31',
            'fact_date': '25-12-2024'  # Неверный формат
        }

        success, message = app_instance.save_goal(goal_data)
        assert not success, "Цель должна быть отклонена из-за неверного формата даты"


# ==================== ТЕСТЫ ДОСТИЖЕНИЙ ====================

class TestAchievementsLogic:
    """Тесты логики достижений"""

    def test_check_achievements_start(self, app_instance):
        """Тест достижения 'Старт'"""
        # Изначально достижение не получено
        app_instance.cursor.execute("SELECT получено FROM достижения WHERE код = 'старт'")
        result = app_instance.cursor.fetchone()
        initial_obtained = result[0]
        assert initial_obtained == 0, "Достижение 'Старт' должно быть не получено изначально"

        # Добавляем цель
        goal_data = {
            'name': 'Первая цель',
            'type': 'Курс',
            'status': 'Планируется',
            'plan_date': '2024-12-31'
        }

        success, _ = app_instance.save_goal(goal_data)
        assert success, "Не удалось добавить цель"

        # Проверяем, что достижение получено
        app_instance.cursor.execute("SELECT получено FROM достижения WHERE код = 'старт'")
        result = app_instance.cursor.fetchone()
        assert result[0] == 1, f"Достижение 'Старт' не активировано. Значение: {result[0]}"

    def test_check_achievements_planner(self, app_instance):
        """Тест достижения 'Планировщик' (5+ целей в процессе)"""
        # Изначально достижение не получено
        app_instance.cursor.execute("SELECT получено FROM достижения WHERE код = 'планировщик'")
        result = app_instance.cursor.fetchone()
        initial_obtained = result[0]
        assert initial_obtained == 0, "Достижение 'Планировщик' должно быть не получено изначально"

        # Добавляем 5 целей в процессе
        for i in range(5):
            goal_data = {
                'name': f'Цель {i+1} в процессе',
                'type': 'Курс',
                'status': 'В процессе',
                'plan_date': f'2024-12-{i+1:02d}'
            }
            success, _ = app_instance.save_goal(goal_data)
            assert success, f"Не удалось добавить цель {i+1}"

        # Проверяем, что достижение получено
        app_instance.cursor.execute("SELECT получено FROM достижения WHERE код = 'планировщик'")
        result = app_instance.cursor.fetchone()
        assert result[0] == 1, f"Достижение 'Планировщик' не активировано. Значение: {result[0]}"

    def test_check_achievements_multi_target(self, app_instance):
        """Тест достижения 'Многоцелевой' (3+ типа целей)"""
        # Изначально достижение не получено
        app_instance.cursor.execute("SELECT получено FROM достижения WHERE код = 'многоцелевой'")
        result = app_instance.cursor.fetchone()
        initial_obtained = result[0]
        assert initial_obtained == 0, "Достижение 'Многоцелевой' должно быть не получено изначально"

        # Добавляем цели 3 разных типов
        goal_types = ['Курс', 'Проект', 'Экзамен']
        for goal_type in goal_types:
            goal_data = {
                'name': f'Цель типа {goal_type}',
                'type': goal_type,
                'status': 'Завершено',
                'plan_date': '2024-01-01',
                'fact_date': '2024-01-01'
            }
            success, _ = app_instance.save_goal(goal_data)
            assert success, f"Не удалось добавить цель типа {goal_type}"

        # Проверяем, что достижение получено
        app_instance.cursor.execute("SELECT получено FROM достижения WHERE код = 'многоцелевой'")
        result = app_instance.cursor.fetchone()
        assert result[0] == 1, f"Достижение 'Многоцелевой' не активировано. Значение: {result[0]}"

    def test_check_achievements_punctual(self, app_instance):
        """Тест достижения 'Пунктуальный' (3+ цели завершены в срок)"""
        # Изначально достижение не получено
        app_instance.cursor.execute("SELECT получено FROM достижения WHERE код = 'пунктуальный'")
        result = app_instance.cursor.fetchone()
        initial_obtained = result[0]
        assert initial_obtained == 0, "Достижение 'Пунктуальный' должно быть не получено изначально"

        # Добавляем 3 цели завершенные в срок (факт <= план)
        for i in range(3):
            goal_data = {
                'name': f'Цель {i+1} в срок',
                'type': 'Курс',
                'status': 'Завершено',
                'plan_date': f'2024-01-{15+i:02d}',
                'fact_date': f'2024-01-{10+i:02d}'  # Завершена раньше срока
            }
            success, _ = app_instance.save_goal(goal_data)
            assert success, f"Не удалось добавить цель {i+1}"

        # Проверяем, что достижение получено
        app_instance.cursor.execute("SELECT получено FROM достижения WHERE код = 'пунктуальный'")
        result = app_instance.cursor.fetchone()
        assert result[0] == 1, f"Достижение 'Пунктуальный' не активировано. Значение: {result[0]}"

    def test_check_achievements_skill_growth(self, app_instance):
        """Тест достижения 'Навыковый рост' (4+ завершенных цели с одним навыком)"""
        # Изначально достижение не получено
        app_instance.cursor.execute("SELECT получено FROM достижения WHERE код = 'навыковый_рост'")
        result = app_instance.cursor.fetchone()
        initial_obtained = result[0]
        assert initial_obtained == 0, "Достижение 'Навыковый рост' должно быть не получено изначально"

        # Сначала добавляем навык
        app_instance.cursor.execute("INSERT OR IGNORE INTO навыки (название) VALUES (?)", ('Python',))
        app_instance.cursor.execute("SELECT id FROM навыки WHERE название = ?", ('Python',))
        skill_id = app_instance.cursor.fetchone()[0]

        # Добавляем 4 завершенные цели с навыком Python
        for i in range(4):
            # Добавляем цель
            goal_data = {
                'name': f'Цель {i+1} с Python',
                'type': 'Курс',
                'status': 'Завершено',
                'plan_date': f'2024-01-{i+1:02d}',
                'fact_date': f'2024-01-{i+1:02d}',
                'skills': ['Python']
            }
            success, _ = app_instance.save_goal(goal_data)
            assert success, f"Не удалось добавить цель {i+1}"

        # Проверяем, что достижение получено
        app_instance.cursor.execute("SELECT получено FROM достижения WHERE код = 'навыковый_рост'")
        result = app_instance.cursor.fetchone()
        assert result[0] == 1, f"Достижение 'Навыковый рост' не активировано. Значение: {result[0]}"


# ==================== ТЕСТЫ ПРОИЗВОДИТЕЛЬНОСТИ ====================

class TestPerformance:
    """Тесты производительности"""

    def test_save_multiple_goals_performance(self, app_instance):
        """Тест производительности при сохранении множества целей"""
        import time

        # Измеряем время сохранения 50 целей (меньше для скорости)
        start_time = time.time()

        for i in range(50):
            goal_data = {
                'name': f'Цель {i}',
                'type': 'Курс',
                'status': 'Завершено',
                'plan_date': '2024-01-01',
                'fact_date': '2024-01-01'
            }
            success, _ = app_instance.save_goal(goal_data)
            assert success, f"Не удалось добавить цель {i}"

        end_time = time.time()
        elapsed = end_time - start_time

        # Сохранение 50 целей должно занимать меньше 1 секунды
        assert elapsed < 1.0, f"Сохранение 50 целей заняло слишком много времени: {elapsed:.2f} секунд"

    def test_refresh_goals_list_performance(self, app_instance):
        """Тест производительности обновления списка целей"""
        import time

        # Сначала добавляем 50 целей
        for i in range(50):
            goal_data = {
                'name': f'Цель {i}',
                'type': 'Курс',
                'status': 'Завершено',
                'plan_date': '2024-01-01',
                'fact_date': '2024-01-01'
            }
            app_instance.save_goal(goal_data)

        # Измеряем время обновления списка
        start_time = time.time()
        goals = app_instance.refresh_goals_list()
        end_time = time.time()
        elapsed = end_time - start_time

        assert len(goals) == 50, f"Ожидалось 50 целей, получено {len(goals)}"
        assert elapsed < 0.05, f"Обновление списка целей заняло слишком много времени: {elapsed:.2f} секунд"


# ==================== ТЕСТЫ ОШИБОК И ВАЛИДАЦИИ ====================

class TestErrorHandling:
    """Тесты обработки ошибок"""

    def test_duplicate_skill_handling(self, app_instance):
        """Тест обработки дублирующихся навыков"""
        # Добавляем навык
        app_instance.cursor.execute(
            "INSERT INTO навыки (название) VALUES (?)",
            ("Python",)
        )
        app_instance.conn.commit()

        # Пытаемся добавить тот же навык снова (должно проигнорироваться из-за UNIQUE constraint)
        try:
            app_instance.cursor.execute(
                "INSERT INTO навыки (название) VALUES (?)",
                ("Python",)
            )
            app_instance.conn.commit()
        except sqlite3.IntegrityError:
            # Это ожидаемое поведение - нарушение UNIQUE constraint
            app_instance.conn.rollback()

        # Теперь используем INSERT OR IGNORE
        app_instance.cursor.execute(
            "INSERT OR IGNORE INTO навыки (название) VALUES (?)",
            ("Python",)
        )
        app_instance.conn.commit()

        # Проверяем, что навык только один
        app_instance.cursor.execute("SELECT COUNT(*) FROM навыки WHERE название = 'Python'")
        count = app_instance.cursor.fetchone()[0]
        assert count == 1, f"Найдено {count} дубликатов навыка 'Python', ожидалось 1"

    def test_invalid_date_validation(self, app_instance):
        """Тест валидации неверных дат"""
        # Несуществующая дата
        goal_data = {
            'name': 'Тестовая цель',
            'type': 'Курс',
            'status': 'В процессе',
            'plan_date': '2024-02-30',  # 30 февраля не существует
        }

        success, message = app_instance.save_goal(goal_data)
        assert not success, "Цель с несуществующей датой должна быть отклонена"
        assert "формат даты" in message.lower() or "дата" in message.lower()

    def test_database_constraints(self, app_instance):
        """Тест ограничений базы данных"""
        # Пытаемся добавить цель без обязательных полей напрямую в БД
        try:
            app_instance.cursor.execute(
                "INSERT INTO цели (название) VALUES (?)",
                ("Цель без типа",)
            )
            app_instance.conn.commit()
            assert False, "Должна быть ошибка NOT NULL constraint"
        except sqlite3.IntegrityError:
            # Это ожидаемое поведение
            app_instance.conn.rollback()
            assert True


# ==================== ИНТЕГРАЦИОННЫЕ ТЕСТЫ ====================

class TestIntegrationScenarios:
    """Интеграционные тесты полных сценариев"""

    def test_complete_goal_workflow(self, app_instance):
        """Полный сценарий работы с целями"""
        # 1. Создаем цель
        goal_data = {
            'name': 'Интеграционный тест',
            'type': 'Проект',
            'status': 'В процессе',
            'plan_date': '2024-12-31',
            'description': 'Тестовое описание',
            'skills': ['Python', 'SQL']
        }

        success, message = app_instance.save_goal(goal_data)
        assert success, f"Не удалось создать цель: {message}"

        # 2. Проверяем, что цель появилась в списке
        goals = app_instance.refresh_goals_list()
        goal_names = [goal[1] for goal in goals]
        assert 'Интеграционный тест' in goal_names, "Цель не найдена в списке"

        # 3. Проверяем, что навыки сохранены
        for skill in goal_data['skills']:
            app_instance.cursor.execute("SELECT 1 FROM навыки WHERE название = ?", (skill,))
            result = app_instance.cursor.fetchone()
            assert result is not None, f"Навык '{skill}' не сохранен"

        # 4. Проверяем достижение 'Старт'
        app_instance.cursor.execute("SELECT получено FROM достижения WHERE код = 'старт'")
        result = app_instance.cursor.fetchone()
        assert result[0] == 1, "Достижение 'Старт' должно быть получено"

    def test_achievements_progressive_unlock(self, app_instance):
        """Тест прогрессивной разблокировки достижений"""
        # Начинаем с 0 целей
        goals_before = app_instance.refresh_goals_list()
        assert len(goals_before) == 0, "Изначально не должно быть целей"

        # Добавляем первую цель - разблокируем 'Старт'
        goal_data = {
            'name': 'Цель 1',
            'type': 'Курс',
            'status': 'В процессе',
            'plan_date': '2024-12-31'
        }
        app_instance.save_goal(goal_data)

        app_instance.cursor.execute("SELECT получено FROM достижения WHERE код = 'старт'")
        result = app_instance.cursor.fetchone()
        assert result[0] == 1, "После первой цели должно быть разблокировано достижение 'Старт'"

        # Добавляем еще 4 цели в процессе - разблокируем 'Планировщик'
        for i in range(2, 6):  # Уже есть 1 цель, нужно еще 4
            goal_data = {
                'name': f'Цель {i}',
                'type': 'Курс',
                'status': 'В процессе',
                'plan_date': f'2024-12-{i:02d}'
            }
            app_instance.save_goal(goal_data)

        app_instance.cursor.execute("SELECT получено FROM достижения WHERE код = 'планировщик'")
        result = app_instance.cursor.fetchone()
        assert result[0] == 1, "После 5 целей в процессе должно быть разблокировано достижение 'Планировщик'"


# ==================== ЗАПУСК ТЕСТОВ ====================

def run_tests():
    """Запуск тестов"""
    print("=" * 80)
    print("ЗАПУСК ТЕСТОВ ДЛЯ ПРИЛОЖЕНИЯ 'ПЛАНИРОВЩИК ИНДИВИДУАЛЬНОГО ОБРАЗОВАТЕЛЬНОГО МАРШРУТА'")
    print("=" * 80)

    # Запускаем pytest
    import pytest
    result = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--no-header",
        "-q"
    ])

    print("\n" + "=" * 80)
    if result == 0:
        print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    else:
        print("НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
    print("=" * 80)

    return result


if __name__ == "__main__":
    # Для отладки можно запускать отдельные тесты
    if len(sys.argv) > 1 and sys.argv[1] == "--debug":
        # Запуск в режиме отладки
        pytest.main([__file__, "-v", "--tb=long"])
    else:
        # Обычный запуск
        run_tests()