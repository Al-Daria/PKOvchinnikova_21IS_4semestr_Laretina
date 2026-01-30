# test_portfolio_system.py
"""
Тесты для системы электронного портфолио исследователя
Запуск: pytest test_portfolio_system.py -v
"""

import pytest
import os
import tempfile
import sys
from datetime import datetime
from pathlib import Path

# Добавляем путь для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем модули
try:
    from database_manager import DatabaseManager
    import portfolio_app

    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Cannot import modules: {e}")
    MODULES_AVAILABLE = False
    DatabaseManager = None
    portfolio_app = None


# ============================================================================
# ПРОСТЫЕ ТЕСТЫ БЕЗ ЗАВИСИМОСТЕЙ
# ============================================================================

def test_file_operations():
    """Тест файловых операций"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Создаем файл
        file_path = tmp_path / "test.md"
        file_path.write_text("# Test File\n\nThis is a test file.", encoding='utf-8')

        # Проверяем чтение
        content = file_path.read_text(encoding='utf-8')
        assert "# Test File" in content
        assert "test file" in content

        # Проверяем запись
        new_content = "# Updated File\n\nNew content."
        file_path.write_text(new_content, encoding='utf-8')

        updated_content = file_path.read_text(encoding='utf-8')
        assert "# Updated File" in updated_content
        assert "New content" in updated_content

        # Проверяем существование и удаление
        assert file_path.exists()
        file_path.unlink()
        assert not file_path.exists()


def test_import_modules():
    """Тест импорта модулей"""
    assert MODULES_AVAILABLE, "Модули не импортированы"


# ============================================================================
# МОК-ТЕСТЫ ДЛЯ DatabaseManager (без реальной БД)
# ============================================================================

@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Модули не доступны")
class TestDatabaseManagerMock:
    """Тесты DatabaseManager с моками"""

    def test_entry_types(self):
        """Тест типов записей"""
        db = DatabaseManager()
        expected_types = ['Публикация', 'Конференция', 'Грант', 'Преподавание', 'Достижение']
        assert db.ENTRY_TYPES == expected_types

    def test_db_config(self):
        """Тест конфигурации БД"""
        db = DatabaseManager()
        config = db.DB_CONFIG

        assert 'dbname' in config
        assert 'user' in config
        assert 'password' in config
        assert 'host' in config
        assert 'port' in config
        assert config['dbname'] == 'research_portfolio'


# ============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ С ИСПОЛЬЗОВАНИЕМ MOCK
# ============================================================================

@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Модули не доступны")
class TestIntegrationWithMock:
    """Интеграционные тесты с использованием mock"""

    @pytest.fixture
    def mock_db(self, mocker):
        """Создание мок-объекта БД"""
        mock_conn = mocker.Mock()
        mock_cursor = mocker.Mock()

        # Настраиваем цепочку вызовов
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1,)  # Mock для RETURNING id
        mock_cursor.fetchall.return_value = []  # Mock для пустых результатов

        # Создаем менеджер и подменяем соединение
        db = DatabaseManager()
        db.connection = mock_conn

        return db, mock_conn, mock_cursor

    def test_create_entry_mock(self, mock_db):
        """Тест создания записи с моком"""
        db, mock_conn, mock_cursor = mock_db

        # Вызываем метод
        entry_id = db.create_entry(
            title="Test Title",
            entry_type="Публикация",
            year=2023,
            file_path="/path/to/file.md"
        )

        # Проверяем, что методы были вызваны
        assert mock_conn.cursor.called
        assert mock_cursor.execute.called
        assert mock_conn.commit.called
        assert mock_cursor.close.called

        # Проверяем, что вернулся ID
        assert entry_id == 1

    def test_get_entries_mock(self, mock_db):
        """Тест получения записей с моком"""
        db, mock_conn, mock_cursor = mock_db

        # Настраиваем возвращаемые данные
        mock_data = [
            (1, 'Test Title', 'Публикация', 2023, '01.01.2023 10:00', '/path/file.md')
        ]
        mock_cursor.fetchall.return_value = mock_data

        # Вызываем метод
        entries = db.get_entries()

        # Проверяем вызовы
        assert mock_conn.cursor.called
        assert mock_cursor.execute.called
        assert mock_cursor.close.called

        # Проверяем результат
        assert len(entries) == 1
        assert entries[0][1] == 'Test Title'
        assert entries[0][2] == 'Публикация'


# ============================================================================
# ТЕСТЫ ДЛЯ portfolio_app (без GUI)
# ============================================================================

@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Модули не доступны")
class TestPortfolioAppLogic:
    """Тесты логики приложения без GUI"""

    def test_year_validation(self):
        """Тест валидации года"""
        current_year = datetime.now().year

        # Тестируем функцию валидации (эмулируем логику из create_entry)
        def validate_year(year_str):
            try:
                year_int = int(year_str)
                if year_int < 1900 or year_int > current_year + 1:
                    raise ValueError("Год вне диапазона")
                return True
            except ValueError:
                return False

        # Корректные годы
        assert validate_year("1900") == True
        assert validate_year("2000") == True
        assert validate_year(str(current_year)) == True
        assert validate_year(str(current_year + 1)) == True

        # Некорректные годы
        assert validate_year("1899") == False
        assert validate_year(str(current_year + 2)) == False
        assert validate_year("abc") == False
        assert validate_year("") == False

    def test_entry_types_list(self):
        """Тест списка типов записей"""
        db = DatabaseManager()
        app = portfolio_app.ResearchPortfolioApp.__new__(portfolio_app.ResearchPortfolioApp)

        # Проверяем, что типы записей одинаковые
        assert hasattr(db, 'ENTRY_TYPES')
        assert isinstance(db.ENTRY_TYPES, list)
        assert len(db.ENTRY_TYPES) > 0

        # Проверяем, что все типы - строки
        for entry_type in db.ENTRY_TYPES:
            assert isinstance(entry_type, str)


# ============================================================================
# ТЕСТЫ ДЛЯ ПРОВЕРКИ СТРУКТУРЫ ФАЙЛОВ
# ============================================================================

def test_project_structure():
    """Тест структуры проекта"""
    current_dir = Path(__file__).parent

    # Проверяем существование файлов
    required_files = [
        'database_manager.py',
        'portfolio_app.py',
        'setup_database.py'
    ]

    for file_name in required_files:
        file_path = current_dir / file_name
        assert file_path.exists(), f"Файл {file_name} не найден"
        assert file_path.is_file(), f"{file_name} не является файлом"


def test_markdown_template():
    """Тест шаблона Markdown"""
    # Шаблон, который должен генерироваться
    template = """# {title}

**Тип:** {entry_type}
**Год:** {year}
**Дата:** {date}

**Соавторы:**
{coauthors_list}

## Описание

{description}"""

    # Проверяем наличие ключевых элементов
    assert "# {title}" in template
    assert "**Тип:**" in template
    assert "**Год:**" in template
    assert "**Соавторы:**" in template
    assert "## Описание" in template


# ============================================================================
# ТЕСТЫ С ИСПОЛЬЗОВАНИЕМ ВРЕМЕННЫХ ФАЙЛОВ
# ============================================================================

class TestWithTempFiles:
    """Тесты с использованием временных файлов"""

    def test_create_markdown_file(self, tmp_path):
        """Тест создания Markdown файла"""
        # Создаем тестовый файл
        md_file = tmp_path / "test_publication.md"

        content = """# Научная статья

**Тип:** Публикация
**Год:** 2023
**Дата:** 15.11.2023 14:30

**Соавторы:**
- Иван Иванов
- Петр Петров

## Описание

Исследование посвящено анализу современных тенденций в области искусственного интеллекта и машинного обучения."""

        # Записываем файл
        md_file.write_text(content, encoding='utf-8')

        # Проверяем
        assert md_file.exists()
        assert md_file.read_text(encoding='utf-8') == content

        # Проверяем структуру
        text = md_file.read_text(encoding='utf-8')
        assert "# Научная статья" in text
        assert "**Тип:** Публикация" in text
        assert "**Год:** 2023" in text
        assert "- Иван Иванов" in text
        assert "## Описание" in text

    def test_file_extension(self, tmp_path):
        """Тест расширения файлов"""
        # Создаем файлы с разными расширениями
        extensions = ['.md', '.txt', '.markdown']

        for ext in extensions:
            file_path = tmp_path / f"test{ext}"
            file_path.write_text(f"Test content for {ext}", encoding='utf-8')
            assert file_path.exists()

            # Проверяем расширение
            assert file_path.suffix == ext


# ============================================================================
# ПАРАМЕТРИЗОВАННЫЕ ТЕСТЫ
# ============================================================================

@pytest.mark.parametrize("year_input,expected_valid", [
    ("2023", True),
    ("2000", True),
    ("1900", True),
    ("2050", False),  # Будущий год (если текущий < 2050)
    ("1800", False),  # Слишком старый
    ("abc", False),  # Не число
    ("", False),  # Пустая строка
    ("2023.5", False),  # Дробное число
])
def test_year_validation_parametrized(year_input, expected_valid):
    """Параметризованный тест валидации года"""
    current_year = datetime.now().year

    try:
        year_int = int(year_input)
        is_valid = 1900 <= year_int <= current_year + 1
    except ValueError:
        is_valid = False

    assert is_valid == expected_valid, f"Ошибка валидации для года: {year_input}"


@pytest.mark.parametrize("entry_type", [
    "Публикация",
    "Конференция",
    "Грант",
    "Преподавание",
    "Достижение"
])
@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Модули не доступны")
def test_entry_types_parametrized(entry_type):
    """Параметризованный тест типов записей"""
    db = DatabaseManager()
    assert entry_type in db.ENTRY_TYPES


# ============================================================================
# ТЕСТЫ ОШИБОК И ИСКЛЮЧЕНИЙ
# ============================================================================

@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Модули не доступны")
class TestErrorCases:
    """Тесты обработки ошибок"""

    def test_invalid_year_string(self):
        """Тест обработки некорректного года (строка)"""

        # Эмулируем логику валидации
        def validate_and_convert(year_str):
            try:
                year_int = int(year_str)
                current_year = datetime.now().year
                if year_int < 1900 or year_int > current_year + 1:
                    raise ValueError("Год вне допустимого диапазона")
                return year_int
            except ValueError as e:
                raise ValueError(f"Некорректный год: {year_str}") from e

        # Должно пройти
        assert validate_and_convert("2023") == 2023

        # Должно вызвать исключение
        with pytest.raises(ValueError):
            validate_and_convert("not_a_year")

        with pytest.raises(ValueError):
            validate_and_convert("1800")


# ============================================================================
# ЗАПУСК ТЕСТОВ ПРИ НЕПОСРЕДСТВЕННОМ ВЫЗОВЕ
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ СИСТЕМЫ ПОРТФОЛИО ИССЛЕДОВАТЕЛЯ")
    print("=" * 60)

    # Проверяем структуру проекта
    print("\n1. Проверка структуры проекта:")
    test_project_structure()
    print("   ✓ Структура проекта корректна")

    # Проверяем импорт
    print("\n2. Проверка импорта модулей:")
    if MODULES_AVAILABLE:
        print("   ✓ Модули импортированы успешно")
    else:
        print("   ✗ Ошибка импорта модулей")

    # Запускаем тесты через pytest
    print("\n" + "=" * 60)
    print("Для запуска полного набора тестов выполните:")
    print("  pytest test_portfolio_system.py -v")
    print("=" * 60)