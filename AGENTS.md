# AGENTS.md

Инструкции для ИИ-агентов и контрибьюторов, работающих с этим репозиторием.

## О проекте

**Deeplink Runner** — настольная утилита для запуска Android deeplink'ов через ADB.
Есть выбор устройства, история запусков, избранное с названиями, импорт/экспорт в JSON.
Интерфейс на русском языке, тёмная тема в цветах VS Code Dark+.

## Стек

- Python 3.9+
- **PySide6** (Qt 6). Проект переведён с PyQt5 — не возвращайте PyQt5/PyQt6 и не смешивайте биндинги.
- Сборка: PyInstaller (`deeplink_runner_qt.spec`, файл в `.gitignore`, но используется локально).

## Структура

```
deeplink_runner_qt.py  # точка входа, UI и логика ADB/данных
theme.py               # палитра, QPalette и QSS темы VS Code Dark+
requirements.txt       # зависимости (PySide6)
README.md              # описание и инструкции для пользователя
sample/preview.png     # скриншот интерфейса (обновляйте при заметных изменениях UI)
```

## Запуск и проверка

```bash
source .venv/bin/activate
pip install -r requirements.txt
python deeplink_runner_qt.py
```

Headless-проверка, что приложение собирается и запускается:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -c "
from PySide6.QtWidgets import QApplication
from theme import apply_theme
import deeplink_runner_qt as m
app = QApplication([])
apply_theme(app)
w = m.DeeplinkLauncher()
w.show()
print('OK')
"
```

Перед коммитом минимум:
- `python -m py_compile deeplink_runner_qt.py theme.py`
- headless-запуск выше без ошибок и предупреждений Qt о QSS.

## Правила разработки

- **Qt6/PySide6 API**: используйте scoped-enum'ы (`QMessageBox.StandardButton.Yes`,
  `QSizePolicy.Policy.Expanding`), `app.exec()` вместо `exec_()`.
- **Тема**: все цвета и стили — в `theme.py`. Не хардкодьте цвета в виджетах;
  для акцентной кнопки используйте `setObjectName("primaryButton")`,
  для опасного действия — `setObjectName("dangerButton")`,
  для приглушённого текста — `setObjectName("mutedLabel")`.
- **UI-тексты** — на русском, в стиле существующих.
- **Данные**: `deeplinks.json` в системной папке приложения (см. `get_app_data_dir()`).
  Ключ `APP_NAME` менять нельзя — это сломает доступ к уже сохранённым данным.
- **ADB**: путь ищется в `resolve_adb()`; учитывайте Windows/macOS/Linux.
  Внешние команды запускайте с `capture_output=True` и таймаутом.
- **Сигналы Qt**: помните, что `clicked` передаёт `bool`. Если слот принимает
  необязательный аргумент (например `refresh_devices(notify=True)`), подключайте
  через `lambda: ...`, иначе `False` попадёт в параметр.
- Не удаляйте пользовательские данные и не выполняйте `adb`-команды, меняющие
  состояние устройства, без явной просьбы.
- Не запускайте GUI-приложения в фоне без необходимости; для проверок используйте
  `QT_QPA_PLATFORM=offscreen`.

## Обновление превью

Скриншот `sample/preview.png` делается headless-рендером окна с демо-данными
(подмените `load_data`/`get_devices_info`), примерно так:

```python
window.grab().save("sample/preview.png")
```

Не коммитьте скриншот с реальными ссылками и серийниками устройств — только демо-данные.

## Git

- Не коммитьте `build/`, `dist/`, `__pycache__/`, `*.spec`, `.venv`.
- Сообщения коммитов — короткие, в стиле истории (`add ...`, `fix ...`, `update ...`).
