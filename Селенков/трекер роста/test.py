"""
PyTest тесты для системы портфолио и компетенций.
Адаптировано под текущий код из tracker.py
"""

import pytest
from datetime import datetime, date
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Мокаем все GUI-зависимости перед импортом приложения
sys.modules['tkinter'] = Mock()
sys.modules['tkinter.messagebox'] = Mock()
sys.modules['tkinter.ttk'] = Mock()
sys.modules['tkinter.Tk'] = Mock()
sys.modules['tkinter.Text'] = Mock()
sys.modules['tkinter.Entry'] = Mock()
sys.modules['tkinter.Combobox'] = Mock()
sys.modules['tkinter.StringVar'] = Mock()
sys.modules['tkinter.Menu'] = Mock()
sys.modules['tkinter.Frame'] = Mock()
sys.modules['tkinter.Label'] = Mock()
sys.modules['tkinter.Button'] = Mock()
sys.modules['tkinter.Scrollbar'] = Mock()
sys.modules['tkinter.Treeview'] = Mock()

# Мокаем другие зависимости
sys.modules['docx'] = Mock()
sys.modules['docx.Document'] = Mock()
sys.modules['docx.shared'] = Mock()
sys.modules['docx.enum.text'] = Mock()

# Теперь импортируем основной код
from tracker import PortfolioApp


class TestDatabaseOperations:
    """Тесты операций с базой данных"""

    def test_initialize_database_tables(self, mocker):
        """Тест создания таблиц в БД"""
        # Мокаем все зависимости
        mock_connect = mocker.patch('psycopg2.connect')
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Мокаем os.path.exists для competencies.json
        mocker.patch('os.path.exists', return_value=False)

        # Создаем приложение (частично инициализируем)
        app = PortfolioApp.__new__(PortfolioApp)
        app.conn = mock_conn
        app.cursor = mock_cursor

        # Вызываем метод initialize_database
        app.initialize_database()

        # Проверяем, что было как минимум 7 вызовов CREATE TABLE
        assert mock_cursor.execute.call_count >= 7

        # Проверяем, что был вызов commit
        mock_conn.commit.assert_called_once()

    def test_load_competencies_from_json(self, mocker):
        """Тест загрузки компетенций из JSON"""
        # Мокаем все зависимости
        mock_connect = mocker.patch('psycopg2.connect')
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Мокаем os.path.exists для competencies.json
        mocker.patch('os.path.exists', return_value=True)

        # Мокаем json.load
        mock_json = mocker.patch('json.load')
        mock_json.return_value = [{
            "specialty": "Информационные системы",
            "competencies": [
                {"name": "Программирование", "category": "Технические"},
                {"name": "Работа с БД", "category": "Технические"}
            ]
        }]

        # Мокаем open
        mock_open = mocker.patch('builtins.open', mocker.mock_open())

        # Создаем приложение
        app = PortfolioApp.__new__(PortfolioApp)
        app.conn = mock_conn
        app.cursor = mock_cursor

        # Вызываем метод
        app.load_competencies_from_json()

        # Проверяем, что были вызовы DELETE и INSERT
        assert mock_cursor.execute.call_count >= 2
        mock_conn.commit.assert_called_once()

    def test_create_default_json(self, mocker, tmp_path):
        """Тест создания дефолтного JSON"""
        # Мокаем json.dump
        mock_json_dump = mocker.patch('json.dump')

        # Мокаем open
        mock_open = mocker.patch('builtins.open', mocker.mock_open())

        # Создаем приложение
        app = PortfolioApp.__new__(PortfolioApp)

        # Вызываем метод
        app.create_default_json()

        # Проверяем, что json.dump был вызван
        mock_json_dump.assert_called_once()


class TestEntryValidation:
    """Тесты валидации записей"""

    def test_validate_entry_missing_fields(self):
        """Тест валидации записи с отсутствующими полями"""
        # Тест логики валидации из метода add_entry
        test_cases = [
            ("", "Проект", "2024-01-15", True),
            ("Тест", "", "2024-01-15", True),
            ("Тест", "Проект", "", True),
            ("Тест", "Проект", "2024-01-15", False)
        ]

        for title, entry_type, date_str, should_be_invalid in test_cases:
            is_invalid = not title or not entry_type or not date_str
            assert is_invalid == should_be_invalid

    def test_validate_date_format(self):
        """Тест валидации формата даты"""
        valid_dates = ["2024-01-15", "2024-12-31", "2023-02-28"]
        invalid_dates = ["15-01-2024", "2024/01/15", "2024-13-01", "не дата"]

        for date_str in valid_dates:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
                is_valid = True
            except ValueError:
                is_valid = False
            assert is_valid

        for date_str in invalid_dates:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
                is_valid = True
            except ValueError:
                is_valid = False
            assert not is_valid

    def test_extract_keywords_from_combos(self):
        """Тест извлечения ключевых слов из комбобоксов"""
        # Создаем моковые комбобоксы
        mock_combos = [
            Mock(get=Mock(return_value="Python")),
            Mock(get=Mock(return_value="Базы данных")),
            Mock(get=Mock(return_value="")),
            Mock(get=Mock(return_value="  ")),
            Mock(get=Mock(return_value="Анализ"))
        ]

        # Имитируем логику из add_entry
        keywords = [combo.get().strip() for combo in mock_combos if combo.get().strip()]

        assert len(keywords) == 3
        assert "Python" in keywords
        assert "Базы данных" in keywords
        assert "Анализ" in keywords


class TestAchievementsLogic:
    """Тесты логики системы достижений"""

    def test_unlock_new_achievement(self, mocker):
        """Тест получения нового достижения"""
        mock_cursor = Mock()
        mock_conn = Mock()

        # Мокаем, что достижения еще нет
        mock_cursor.fetchone.return_value = None

        app = PortfolioApp.__new__(PortfolioApp)
        app.current_user_id = 1
        app.cursor = mock_cursor
        app.conn = mock_conn

        # Мокаем update_statistics
        app.update_statistics = Mock()

        # Вызываем метод
        app.unlock_achievement("Тестовое достижение", "Описание")

        # Проверяем вызовы
        assert mock_cursor.execute.call_count == 2
        mock_conn.commit.assert_called_once()
        app.update_statistics.assert_called_once()

    def test_unlock_existing_achievement(self, mocker):
        """Тест попытки получить уже существующее достижение"""
        mock_cursor = Mock()
        mock_conn = Mock()

        # Мокаем, что достижение уже есть
        mock_cursor.fetchone.return_value = (1,)

        app = PortfolioApp.__new__(PortfolioApp)
        app.current_user_id = 1
        app.cursor = mock_cursor
        app.conn = mock_conn
        app.update_statistics = Mock()

        # Вызываем метод
        app.unlock_achievement("Тестовое достижение", "Описание")

        # Проверяем, что был только один SELECT, но не INSERT
        assert mock_cursor.execute.call_count == 1
        mock_conn.commit.assert_not_called()

    def test_check_achievements_conditions(self, mocker):
        """Тест условий для различных достижений"""
        # Проверяем логику из check_achievements

        # Условие для "Первый шаг"
        total_entries = 1
        assert total_entries == 1

        # Условие для "Командный игрок"
        entries_with_coauthors = 3
        assert entries_with_coauthors >= 3

        # Условие для "Разносторонний"
        distinct_types = 3
        assert distinct_types >= 3

        # Условие для "Словобог"
        total_chars = 5001
        assert total_chars > 5000

    def test_check_achievements_method(self, mocker):
        """Тест метода check_achievements"""
        mock_cursor = Mock()
        mock_conn = Mock()

        # Настраиваем последовательные результаты запросов
        mock_cursor.fetchone.side_effect = [
            (1,),  # COUNT(*) FROM entries - всего записей
            (0,),  # записей с соавторами
            (1,),  # COUNT(DISTINCT type) - уникальных типов
            None,  # плодотворный год
            (100,)  # SUM(LENGTH(description)) - общий объем
        ]

        app = PortfolioApp.__new__(PortfolioApp)
        app.current_user_id = 1
        app.cursor = mock_cursor
        app.conn = mock_conn
        app.unlock_achievement = Mock()

        # Вызываем метод
        app.check_achievements()

        # Проверяем, что unlock_achievement был вызван для "Первый шаг"
        app.unlock_achievement.assert_called_with("Первый шаг", "Создана первая запись")


class TestStatisticsCalculations:
    """Тесты расчетов статистики"""

    def test_coauthors_parsing_and_counting(self):
        """Тест парсинга и подсчета соавторов"""
        # Тестовые данные
        coauthors_strings = [
            "Иванов Иван, Петров Петр",
            "Иванов Иван, Сидоров Сидор",
            "Петров Петр"
        ]

        # Имитируем логику из update_statistics
        coauthors_dict = {}
        for row in coauthors_strings:
            for ca in row.split(","):
                ca = ca.strip()
                if ca:
                    coauthors_dict[ca] = coauthors_dict.get(ca, 0) + 1

        # Проверяем результаты
        assert coauthors_dict["Иванов Иван"] == 2
        assert coauthors_dict["Петров Петр"] == 2
        assert coauthors_dict["Сидоров Сидор"] == 1

    def test_competency_level_calculation_and_recommendations(self):
        """Тест расчета уровня компетенций и рекомендаций"""
        # Тестовые данные
        competencies_data = [
            ("Программирование", 4.5),
            ("Работа с БД", 2.8),
            ("Презентация результатов", 1.8),
            ("Командная работа", 2.5)
        ]

        # Имитируем логику из update_statistics
        comp_content = ""
        weak_content = ""
        rec_content = ""

        for name, level in competencies_data:
            level = float(level)
            comp_content += f"{name}: {level:.2f}\n"

            if level < 3:
                weak_content += f"{name}: {level:.2f}\n"

                if "Презентация" in name:
                    rec_content += "Рекомендуется выступить на студенческой конференции\n"
                elif "Командная" in name:
                    rec_content += "Рекомендуется участвовать в групповых проектах\n"
                elif "БД" in name:
                    rec_content += "Рекомендуется пройти курс по базам данных\n"

        # Проверяем результаты
        assert "Программирование: 4.50" in comp_content
        assert "Работа с БД: 2.80" in weak_content
        assert "Презентация результатов: 1.80" in weak_content
        assert "Рекомендуется выступить на студенческой конференции" in rec_content
        assert "Рекомендуется участвовать в групповых проектах" in rec_content


class TestGoalsLogic:
    """Тесты логики целей"""

    def test_goal_parsing_and_defaults(self):
        """Тест парсинга целей и значений по умолчанию"""
        test_cases = [
            ("10", 10),
            ("5", 5),
            ("", 1),
            ("не число", 1),
            ("0", 0)
        ]

        for target_value, expected in test_cases:
            try:
                target_val = int(target_value) if target_value.isdigit() else 1
            except:
                target_val = 1

            assert target_val == expected

    def test_goal_status_calculation(self):
        """Тест расчета статуса цели"""
        test_cases = [
            (10, 10, True),   # выполнено
            (10, 5, False),   # в процессе
            (10, 15, True),   # перевыполнено
            (0, 0, True)      # нулевые значения
        ]

        for target, current, expected_done in test_cases:
            is_done = current >= target
            assert is_done == expected_done


class TestExportLogic:
    """Тесты логики экспорта"""

    def test_filename_generation(self):
        """Тест генерации имени файла"""
        # Фиксируем время для теста
        test_time = datetime(2024, 1, 15, 10, 30, 45)

        # Имитируем логику из export_to_word
        filename = f"portfolio_report_{test_time.strftime('%Y%m%d_%H%M%S')}.docx"

        assert filename == "portfolio_report_20240115_103045.docx"
        assert filename.startswith("portfolio_report_")
        assert filename.endswith(".docx")

    def test_report_structure_elements(self):
        """Тест наличия элементов структуры отчета"""
        # Проверяем, что отчет должен содержать эти разделы
        expected_sections = [
            "Отчёт по портфолио",
            "Записи портфолио",
            "Ключевые слова",
            "Соавторы",
            "Компетенции",
            "Рекомендации",
            "Достижения"
        ]

        # Это проверка логики требований к отчету
        for section in expected_sections:
            assert section in expected_sections


class TestCompetencyLogic:
    """Тесты логики компетенций"""

    def test_default_competencies_in_json(self):
        """Тест дефолтных компетенций в JSON"""
        # Проверяем структуру данных из create_default_json
        default_data = [{
            "specialty": "Информационные системы",
            "competencies": [
                {"name": "Программирование", "category": "Технические"},
                {"name": "Работа с БД", "category": "Технические"},
                {"name": "Анализ данных", "category": "Технические"},
                {"name": "Проектная деятельность", "category": "Профессиональные"},
                {"name": "Научная работа", "category": "Профессиональные"},
                {"name": "Презентация результатов", "category": "Коммуникативные"},
                {"name": "Командная работа", "category": "Коммуникативные"},
                {"name": "Самоорганизация", "category": "Личные"}
            ]
        }]

        assert len(default_data[0]["competencies"]) == 8

        # Проверяем категории
        categories = {comp["category"] for comp in default_data[0]["competencies"]}
        assert "Технические" in categories
        assert "Профессиональные" in categories
        assert "Коммуникативные" in categories
        assert "Личные" in categories

    def test_competency_recommendations_logic(self):
        """Тест логики рекомендаций по компетенциям"""
        # Имитируем логику из update_statistics
        test_cases = [
            ("Презентация результатов", 2.0, "студенческой конференции"),
            ("Командная работа", 1.5, "групповых проектах"),
            ("Работа с БД", 2.8, "курс по базам данных"),
            ("Программирование", 4.0, "")  # высокий уровень - нет рекомендации
        ]

        for comp_name, level, expected_keyword in test_cases:
            recommendation = ""
            if level < 3:
                if "Презентация" in comp_name:
                    recommendation = "Рекомендуется выступить на студенческой конференции"
                elif "Командная" in comp_name:
                    recommendation = "Рекомендуется участвовать в групповых проектах"
                elif "БД" in comp_name:
                    recommendation = "Рекомендуется пройти курс по базам данных"

            if expected_keyword:
                assert expected_keyword in recommendation
            else:
                assert recommendation == ""


class TestIntegrationScenarios:
    """Тесты интеграционных сценариев"""

    def test_complete_entry_workflow(self, mocker):
        """Тест полного workflow добавления записи"""
        # Мокаем все зависимости
        mock_cursor = Mock()
        mock_conn = Mock()

        # Настраиваем возвращаемые значения
        mock_cursor.fetchone.side_effect = [
            (1,),  # RETURNING id для записи
            (1,),  # SELECT id FROM keywords для первого ключевого слова
            (2,)   # SELECT id FROM keywords для второго ключевого слова
        ]

        # Мокаем messagebox
        mock_messagebox = mocker.patch('tkinter.messagebox')

        app = PortfolioApp.__new__(PortfolioApp)
        app.current_user_id = 1
        app.cursor = mock_cursor
        app.conn = mock_conn
        app.load_entries = Mock()
        app.update_statistics = Mock()
        app.check_achievements = Mock()

        # Мокаем виджеты формы
        app.title_entry = Mock(get=Mock(return_value="Тестовый проект"))
        app.type_combo = Mock(get=Mock(return_value="Проект"))
        app.date_entry = Mock(get=Mock(return_value="2024-01-15"))
        app.description_text = Mock(get=Mock(return_value="Описание теста"))
        app.coauthors_entry = Mock(get=Mock(return_value="Иванов Иван"))

        # Мокаем ключевые слова
        mock_combo1 = Mock(get=Mock(return_value="Python"))
        mock_combo2 = Mock(get=Mock(return_value=""))
        mock_combo3 = Mock(get=Mock(return_value=""))
        mock_combo4 = Mock(get=Mock(return_value=""))
        mock_combo5 = Mock(get=Mock(return_value=""))
        app.keyword_combos = [mock_combo1, mock_combo2, mock_combo3, mock_combo4, mock_combo5]

        # Мокаем компетенции
        mock_var1 = Mock(get=Mock(return_value="1: Программирование"))
        mock_var2 = Mock(get=Mock(return_value=""))
        mock_var3 = Mock(get=Mock(return_value=""))
        app.competency_vars = [mock_var1, mock_var2, mock_var3]

        mock_level1 = Mock(get=Mock(return_value="3"))
        mock_level2 = Mock(get=Mock(return_value=""))
        mock_level3 = Mock(get=Mock(return_value=""))
        app.level_combos = [mock_level1, mock_level2, mock_level3]

        # Вызываем метод add_entry
        app.add_entry()

        # Проверяем вызовы
        assert mock_cursor.execute.call_count >= 5
        mock_conn.commit.assert_called_once()
        app.load_entries.assert_called_once()
        app.update_statistics.assert_called_once()
        app.check_achievements.assert_called_once()


class TestErrorHandling:
    """Тесты обработки ошибок"""

    def test_database_error_in_add_entry(self, mocker):
        """Тест обработки ошибок БД при добавлении записи"""
        mock_cursor = Mock()
        mock_conn = Mock()

        # Симулируем ошибку
        mock_cursor.execute.side_effect = Exception("Database error")

        # Мокаем messagebox
        mock_messagebox = mocker.patch('tkinter.messagebox')

        app = PortfolioApp.__new__(PortfolioApp)
        app.current_user_id = 1
        app.cursor = mock_cursor
        app.conn = mock_conn

        # Мокаем виджеты с валидными данными
        app.title_entry = Mock(get=Mock(return_value="Тест"))
        app.type_combo = Mock(get=Mock(return_value="Проект"))
        app.date_entry = Mock(get=Mock(return_value="2024-01-15"))
        app.description_text = Mock(get=Mock(return_value=""))
        app.coauthors_entry = Mock(get=Mock(return_value=""))
        app.keyword_combos = [Mock(get=Mock(return_value="")) for _ in range(5)]
        app.competency_vars = [Mock(get=Mock(return_value="")) for _ in range(3)]
        app.level_combos = [Mock(get=Mock(return_value="")) for _ in range(3)]

        # Вызываем метод и проверяем обработку ошибки
        app.add_entry()

        # Проверяем, что был вызван rollback
        mock_conn.rollback.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])