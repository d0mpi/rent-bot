import os
from pathlib import Path

def get_directory_structure(root_dir: str) -> dict:
    """
    Рекурсивно обходит директорию и создает словарь с её структурой (только .py файлы, исключая venv и сам скрипт).
    """
    structure = {}
    root_path = Path(root_dir).resolve()
    script_name = "export_project.py"  # Имя текущего скрипта

    for item in root_path.rglob("*.py"):
        # Пропускаем временные файлы, venv, export_project, сам скрипт и скрытые файлы
        if any(part in ("__pycache__", "venv", "export_project") for part in item.parts) or \
           item.name == script_name or item.name.startswith("."):
            continue

        relative_path = item.relative_to(root_path)
        parts = relative_path.parts

        current = structure
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        last_part = parts[-1]
        current[last_part] = "file"

    return structure

def dict_to_text(d: dict, indent: int = 0) -> str:
    """
    Преобразует словарь в текстовую строку с отступами, без кавычек для ключей.
    """
    result = []
    indent_str = "  " * indent

    for key, value in d.items():
        if isinstance(value, dict):
            result.append(f"{indent_str}{key}:")
            result.append(dict_to_text(value, indent + 1))
        else:
            result.append(f"{indent_str}{key}: {value}")

    return "\n".join(result)

def get_file_contents(root_dir: str) -> dict:
    """
    Рекурсивно обходит директорию и собирает содержимое только .py файлов, исключая venv и сам скрипт.
    """
    contents = {}
    root_path = Path(root_dir).resolve()
    script_name = "export_project.py"  # Имя текущего скрипта

    for item in root_path.rglob("*.py"):
        # Пропускаем временные файлы, venv, export_project, сам скрипт и скрытые файлы
        if any(part in ("__pycache__", "venv", "export_project") for part in item.parts) or \
           item.name == script_name or item.name.startswith("."):
            continue

        relative_path = str(item.relative_to(root_path)).replace(os.sep, "/")
        
        try:
            with open(item, 'r', encoding='utf-8') as f:
                file_content = f.read()
            contents[relative_path] = file_content
        except PermissionError as e:
            print(f"Нет доступа к файлу {relative_path}: {e}")
            contents[relative_path] = f"Ошибка доступа: {str(e)}"
        except FileNotFoundError as e:
            print(f"Файл не найден {relative_path}: {e}")
            contents[relative_path] = f"Ошибка: файл не найден {str(e)}"
        except UnicodeDecodeError as e:
            print(f"Ошибка декодирования {relative_path}: {e}")
            contents[relative_path] = f"Ошибка декодирования: {str(e)}"
        except Exception as e:
            print(f"Неизвестная ошибка при чтении {relative_path}: {e}")
            contents[relative_path] = f"Неизвестная ошибка: {str(e)}"

    return contents

def contents_to_text(contents: dict) -> str:
    """
    Преобразует содержимое файлов в текстовую строку с разделителями.
    """
    result = []
    for file_path, content in contents.items():
        result.append(f"--- {file_path} ---")
        result.append(content)
        result.append("")
    return "\n".join(result)

def save_to_file(data: str, output_file: str) -> None:
    """
    Сохраняет данные в текстовый файл.
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(data)
    except PermissionError as e:
        print(f"Ошибка записи в файл {output_file}: {e}")
    except Exception as e:
        print(f"Неизвестная ошибка при записи в {output_file}: {e}")

def main():
    # Корневая директория проекта (на уровень выше от скрипта)
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent.resolve()
    
    # Папка для сохранения результатов
    output_dir = script_dir
    output_structure_file = output_dir / "project_structure.txt"
    output_contents_file = output_dir / "project_contents.txt"

    # Получаем структуру
    structure = get_directory_structure(project_dir)
    structure_text = dict_to_text(structure)
    save_to_file(structure_text, output_structure_file)
    print(f"Структура проекта сохранена в {output_structure_file}")

    # Получаем содержимое файлов
    contents = get_file_contents(project_dir)
    contents_text = contents_to_text(contents)
    save_to_file(contents_text, output_contents_file)
    print(f"Содержимое проекта сохранено в {output_contents_file}")

if __name__ == "__main__":
    main()