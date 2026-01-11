#!/usr/bin/env python3

import json
import os
import shutil
import subprocess
import sys

from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "ADB Deeplink Launcher"


def resolve_adb():
    candidates = [
        "adb",  # если вдруг повезёт
        "/opt/homebrew/bin/adb",  # macOS Apple Silicon
        "/usr/local/bin/adb",  # macOS Intel
        "/usr/bin/adb",  # редко, но бывает
    ]

    # Windows
    if sys.platform.startswith("win"):
        candidates.extend(
            [
                os.path.join(
                    os.environ.get("LOCALAPPDATA", ""),
                    "Android",
                    "Sdk",
                    "platform-tools",
                    "adb.exe",
                ),
                os.path.join(
                    os.environ.get("ProgramFiles", ""),
                    "Android",
                    "platform-tools",
                    "adb.exe",
                ),
            ]
        )

    # Linux
    if sys.platform.startswith("linux"):
        candidates.extend(["/usr/bin/adb", "/bin/adb"])

    for path in candidates:
        if shutil.which(path) or os.path.exists(path):
            return path

    return None


def get_app_data_dir():
    if sys.platform == "darwin":  # macOS
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    elif sys.platform.startswith("win"):  # Windows
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:  # Linux и остальные
        base = os.path.join(os.path.expanduser("~"), ".local", "share")

    app_dir = os.path.join(base, APP_NAME)
    os.makedirs(app_dir, exist_ok=True)
    return app_dir


ADB_PATH = resolve_adb()
DATA_FILE = os.path.join(get_app_data_dir(), "deeplinks.json")


# ---------- ADB ----------
def get_devices_info():
    devices = []

    if not ADB_PATH:
        return

    try:
        result = subprocess.run(
            [ADB_PATH, "devices", "-l"], capture_output=True, text=True, check=True
        )

        lines = result.stdout.strip().splitlines()[1:]

        for line in lines:
            if "device" not in line:
                continue

            parts = line.split()
            serial = parts[0]

            info = {"serial": serial, "model": "Unknown", "android": "?"}

            # model из adb devices -l
            for part in parts:
                if part.startswith("model:"):
                    info["model"] = part.replace("model:", "").replace("_", " ")

            # версия Android
            try:
                version = subprocess.run(
                    [
                        ADB_PATH,
                        "-s",
                        serial,
                        "shell",
                        "getprop",
                        "ro.build.version.release",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=2,
                ).stdout.strip()

                if version:
                    info["android"] = version
            except Exception:
                pass

            devices.append(info)

    except Exception:
        pass

    return devices


def run_deeplink(device, deeplink):
    if not ADB_PATH:
        return
    cmd = [ADB_PATH]
    if device:
        cmd += ["-s", device]

    cmd += ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", deeplink]
    subprocess.run(cmd, check=True)


# ---------- Data ----------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"history": [], "favorites": []}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"history": [], "favorites": []}


def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        QMessageBox.critical(
            None, "Ошибка сохранения", f"Не удалось сохранить данные:\n{e}"
        )


# ---------- UI ----------
class DeeplinkLauncher(QWidget):
    def __init__(self):
        super().__init__()

        self.devices = get_devices_info()
        self.data = load_data()

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(900, 500)

        self.init_ui()
        self.refresh_devices()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        import_btn = QPushButton("📥 Импорт файла")
        import_btn.clicked.connect(self.import_deeplinks)

        export_btn = QPushButton("📤 Экспорт файла")
        export_btn.clicked.connect(self.export_deeplinks)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(import_btn)
        buttons_layout.addWidget(export_btn)
        main_layout.addLayout(buttons_layout)

        # Device selector
        if len(self.devices) > 0:
            device_layout = QHBoxLayout()
            device_layout.addWidget(QLabel("Устройство:"))

            self.device_combo = QComboBox()
            for device in self.devices:
                self.device_combo.addItem(self.format_device(device), device["serial"])

            refresh_btn = QPushButton("Обновить")
            refresh_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
            refresh_btn.setToolTip("Обновить список устройств")
            refresh_btn.clicked.connect(self.refresh_devices)

            device_layout.addWidget(self.device_combo)
            device_layout.addWidget(refresh_btn)

            main_layout.addLayout(device_layout)
        else:
            self.device_combo = None

        # Deeplink input
        main_layout.addWidget(QLabel("Deeplink:"))
        self.deeplink_input = QLineEdit()
        self.deeplink_input.setClearButtonEnabled(True)
        main_layout.addWidget(self.deeplink_input)

        # Buttons
        buttons_layout = QHBoxLayout()

        launch_btn = QPushButton("Запустить")
        launch_btn.clicked.connect(self.launch)

        fav_btn = QPushButton("В избранное")
        fav_btn.clicked.connect(self.add_to_favorites)

        buttons_layout.addWidget(launch_btn)
        buttons_layout.addWidget(fav_btn)

        main_layout.addLayout(buttons_layout)

        # Lists
        lists_layout = QHBoxLayout()

        # History
        history_box = QGroupBox("История")
        history_layout = QVBoxLayout(history_box)

        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self.launch_from_history)
        self.history_list.itemClicked.connect(self.fill_from_history)

        for link in self.data["history"]:
            self.history_list.addItem(link)

        clear_history_btn = QPushButton("Очистить историю")
        clear_history_btn.clicked.connect(self.clear_history)

        history_layout.addWidget(self.history_list)
        history_layout.addWidget(clear_history_btn)

        # Favorites
        favorites_box = QGroupBox("Избранное")
        favorites_layout = QVBoxLayout(favorites_box)

        self.favorites_list = QListWidget()
        self.favorites_list.itemDoubleClicked.connect(self.launch_from_favorite)
        self.favorites_list.itemClicked.connect(self.fill_from_favorite)

        for fav in self.data["favorites"]:
            self.favorites_list.addItem(self.format_favorite(fav))

        rename_btn = QPushButton("Переименовать")
        rename_btn.clicked.connect(self.rename_favorite)

        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(self.delete_favorite)

        clear_btn = QPushButton("Удалить все")
        clear_btn.clicked.connect(self.clear_favorite)

        favorites_layout.addWidget(self.favorites_list)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(rename_btn)
        buttons_layout.addWidget(delete_btn)
        buttons_layout.addWidget(clear_btn)

        favorites_layout.addLayout(buttons_layout)

        lists_layout.addWidget(history_box)
        lists_layout.addWidget(favorites_box)

        main_layout.addLayout(lists_layout)

    def refresh_devices(self):
        current_serial = self.current_device()

        self.devices = get_devices_info()

        if not self.devices:
            QMessageBox.information(
                self,
                "ADB",
                "Устройства не найдены.\n\n"
                "Проверьте, что:\n"
                "• adb установлен\n"
                "• устройство подключено\n"
                "• включён USB debugging",
            )

        if not self.device_combo:
            return

        self.device_combo.blockSignals(True)
        self.device_combo.clear()

        for device in self.devices:
            self.device_combo.addItem(self.format_device(device), device["serial"])

        # попытка восстановить выбранное устройство
        if current_serial:
            index = self.device_combo.findData(current_serial)
            if index >= 0:
                self.device_combo.setCurrentIndex(index)

        self.device_combo.blockSignals(False)

    # ---------- Actions ----------
    def current_device(self):
        if self.device_combo:
            return self.device_combo.currentData()
        return None

    def launch(self):
        deeplink = self.deeplink_input.text().strip()
        if not deeplink:
            QMessageBox.warning(self, "Ошибка", "Введите диплинк")
            return

        try:
            run_deeplink(self.current_device(), deeplink)
        except Exception as e:
            QMessageBox.critical(self, "ADB error", str(e))
            return

        if deeplink not in self.data["history"]:
            self.data["history"].insert(0, deeplink)
            self.history_list.insertItem(0, deeplink)
            save_data(self.data)

    def add_to_favorites(self):
        deeplink = self.deeplink_input.text().strip()
        if not deeplink:
            return

        name, ok = QInputDialog.getText(self, "Название", "Введите название:")
        if not ok or not name:
            return

        fav = {"name": name, "deeplink": deeplink}
        self.data["favorites"].append(fav)
        self.favorites_list.addItem(self.format_favorite(fav))
        save_data(self.data)

    def rename_favorite(self):
        row = self.favorites_list.currentRow()
        if row < 0:
            return

        fav = self.data["favorites"][row]

        new_name, ok = QInputDialog.getText(
            self, "Переименовать", "Новое название:", text=fav["name"]
        )
        if not ok or not new_name:
            return

        fav["name"] = new_name
        self.favorites_list.item(row).setText(self.format_favorite(fav))
        save_data(self.data)

    def delete_favorite(self):
        row = self.favorites_list.currentRow()
        if row < 0:
            return

        fav = self.data["favorites"][row]

        reply = QMessageBox.question(
            self,
            "Удалить",
            f"Удалить избранное:\n\n{fav['name']}?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            del self.data["favorites"][row]
            self.favorites_list.takeItem(row)
            save_data(self.data)

    def clear_favorite(self):
        reply = QMessageBox.question(
            self,
            "Удалить",
            "Удалить все диплинки из избранного?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.data["favorites"].clear()
            self.favorites_list.clear()
            save_data(self.data)

    def clear_history(self):
        if not self.data["history"]:
            return

        reply = QMessageBox.question(
            self,
            "Очистить историю",
            "Вы уверены, что хотите очистить историю?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.data["history"].clear()
            self.history_list.clear()
            save_data(self.data)

    def fill_from_history(self, item):
        deeplink = item.text()
        self.deeplink_input.setText(deeplink)

    def launch_from_history(self, item):
        deeplink = item.text()
        self.deeplink_input.setText(deeplink)
        self.launch()

    def launch_from_favorite(self, item):
        row = self.favorites_list.currentRow()
        fav = self.data["favorites"][row]
        self.deeplink_input.setText(fav["deeplink"])
        self.launch()

    def fill_from_favorite(self, item):
        row = self.favorites_list.currentRow()
        fav = self.data["favorites"][row]
        self.deeplink_input.setText(fav["deeplink"])

    @staticmethod
    def format_favorite(fav):
        return f"{fav['name']}  →  {fav['deeplink']}"

    @staticmethod
    def format_device(device):
        return f"{device['serial']} | {device['model']} | Android {device['android']}"

    def export_deeplinks(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт диплинков", "deeplinks.json", "JSON files (*.json)"
        )

        if not path:
            return

        export_data = {
            "version": 1,
            "history": self.data.get("history", []),
            "favorites": self.data.get("favorites", []),
        }

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))
            return

        QMessageBox.information(self, "Экспорт", "Диплинки успешно экспортированы")

    def import_deeplinks(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Импорт диплинков", "", "JSON files (*.json)"
        )

        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                imported = json.load(f)
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка импорта", f"Не удалось прочитать файл:\n{e}"
            )
            return

        if not isinstance(imported, dict) or "favorites" not in imported:
            QMessageBox.critical(self, "Ошибка", "Некорректный формат файла")
            return

        # --- merge ---
        added_fav = 0
        for fav in imported.get("favorites", []):
            if fav not in self.data["favorites"]:
                self.data["favorites"].append(fav)
                self.favorites_list.addItem(self.format_favorite(fav))
                added_fav += 1

        added_hist = 0
        for link in imported.get("history", []):
            if link not in self.data["history"]:
                self.data["history"].append(link)
                self.history_list.addItem(link)
                added_hist += 1

        save_data(self.data)

        QMessageBox.information(
            self,
            "Импорт завершён",
            f"Добавлено:\n• Избранное: {added_fav}\n• История: {added_hist}",
        )


# ---------- Run ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DeeplinkLauncher()
    window.show()
    sys.exit(app.exec_())
