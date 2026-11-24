#!/usr/bin/env python3

import json
import os
import shutil
import subprocess
import sys

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from theme import apply_theme

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
        return devices

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
        raise RuntimeError("adb не найден. Установите Android platform-tools.")

    cmd = [ADB_PATH]
    if device:
        cmd += ["-s", device]

    cmd += ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", deeplink]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    output = (result.stdout + result.stderr).strip()

    if result.returncode != 0 or "Error:" in output or "Error type" in output:
        raise RuntimeError(output or f"adb завершился с кодом {result.returncode}")


# ---------- Data ----------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"history": [], "favorites": []}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"history": [], "favorites": []}

    if not isinstance(data, dict):
        return {"history": [], "favorites": []}

    data.setdefault("history", [])
    data.setdefault("favorites", [])
    return data


def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        QMessageBox.critical(
            None, "Ошибка сохранения", f"Не удалось сохранить данные:\n{e}"
        )


# ---------- UI ----------
class DeeplinkLauncher(QMainWindow):
    def __init__(self):
        super().__init__()

        self.adb_path = ADB_PATH
        self.devices = get_devices_info()
        self.data = load_data()

        self.setWindowTitle(APP_NAME)
        self.resize(960, 620)
        self.setMinimumSize(820, 480)

        self.init_ui()
        self.refresh_devices(notify=False)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 14, 16, 12)
        main_layout.setSpacing(12)

        # ---------- Header ----------
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        title = QLabel("Deeplink Runner")
        title.setObjectName("appTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()

        import_btn = QPushButton("Импорт…")
        import_btn.setToolTip("Импортировать диплинки из JSON-файла")
        import_btn.clicked.connect(self.import_deeplinks)

        export_btn = QPushButton("Экспорт…")
        export_btn.setToolTip("Экспортировать историю и избранное в JSON-файл")
        export_btn.clicked.connect(self.export_deeplinks)

        header_layout.addWidget(import_btn)
        header_layout.addWidget(export_btn)
        main_layout.addLayout(header_layout)

        # ---------- Device selector ----------
        device_layout = QHBoxLayout()
        device_layout.setSpacing(8)

        device_label = QLabel("Устройство:")
        device_layout.addWidget(device_label)

        self.device_combo = QComboBox()
        self.device_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.device_combo.setMinimumWidth(280)
        device_layout.addWidget(self.device_combo, 1)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        refresh_btn.setToolTip("Обновить список устройств")
        refresh_btn.clicked.connect(lambda: self.refresh_devices())
        device_layout.addWidget(refresh_btn)

        main_layout.addLayout(device_layout)

        # ---------- Deeplink input ----------
        input_label_layout = QHBoxLayout()
        input_label_layout.addWidget(QLabel("Deeplink:"))

        hint_label = QLabel("Enter — запустить, двойной клик по записи — открыть")
        hint_label.setObjectName("mutedLabel")
        input_label_layout.addStretch()
        input_label_layout.addWidget(hint_label)

        main_layout.addLayout(input_label_layout)

        self.deeplink_input = QLineEdit()
        self.deeplink_input.setObjectName("deeplinkInput")
        self.deeplink_input.setPlaceholderText("myapp://open/screen?id=42")
        self.deeplink_input.setClearButtonEnabled(True)
        self.deeplink_input.returnPressed.connect(self.launch)
        main_layout.addWidget(self.deeplink_input)

        # ---------- Action buttons ----------
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        launch_btn = QPushButton("Запустить")
        launch_btn.setObjectName("primaryButton")
        launch_btn.setToolTip("Отправить deeplink на выбранное устройство")
        launch_btn.clicked.connect(self.launch)

        fav_btn = QPushButton("В избранное")
        fav_btn.setToolTip("Сохранить deeplink в избранное")
        fav_btn.clicked.connect(self.add_to_favorites)

        actions_layout.addWidget(launch_btn)
        actions_layout.addWidget(fav_btn)
        actions_layout.addStretch()

        main_layout.addLayout(actions_layout)

        # ---------- Lists ----------
        lists_layout = QHBoxLayout()
        lists_layout.setSpacing(12)

        # History
        history_box = QGroupBox("История")
        history_layout = QVBoxLayout(history_box)
        history_layout.setSpacing(8)

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
        favorites_layout.setSpacing(8)

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
        clear_btn.setObjectName("dangerButton")
        clear_btn.clicked.connect(self.clear_favorite)

        favorites_layout.addWidget(self.favorites_list)

        fav_buttons_layout = QHBoxLayout()
        fav_buttons_layout.setSpacing(8)
        fav_buttons_layout.addWidget(rename_btn)
        fav_buttons_layout.addWidget(delete_btn)
        fav_buttons_layout.addWidget(clear_btn)

        favorites_layout.addLayout(fav_buttons_layout)

        lists_layout.addWidget(history_box)
        lists_layout.addWidget(favorites_box)

        main_layout.addLayout(lists_layout, 1)

        self.update_status()

    # ---------- Devices ----------
    def current_device(self):
        return self.device_combo.currentData()

    def refresh_devices(self, notify=True):
        current_serial = self.current_device()

        self.devices = get_devices_info()

        self.device_combo.blockSignals(True)
        self.device_combo.clear()

        if self.devices:
            for device in self.devices:
                self.device_combo.addItem(self.format_device(device), device["serial"])

            # попытка восстановить выбранное устройство
            if current_serial:
                index = self.device_combo.findData(current_serial)
                if index >= 0:
                    self.device_combo.setCurrentIndex(index)

            self.device_combo.setEnabled(True)
        else:
            self.device_combo.addItem("Устройства не найдены", None)
            self.device_combo.setEnabled(False)

        self.device_combo.blockSignals(False)
        self.update_status()

        if notify and not self.devices:
            QMessageBox.information(
                self,
                "ADB",
                "Устройства не найдены.\n\n"
                "Проверьте, что:\n"
                "• adb установлен\n"
                "• устройство подключено\n"
                "• включён USB debugging",
            )

    def update_status(self):
        if not self.adb_path:
            text = "ADB не найден — запуск недоступен"
        elif not self.devices:
            text = "ADB: устройства не найдены"
        else:
            serial = self.current_device()
            text = f"ADB: устройств — {len(self.devices)}"
            if serial:
                text += f" • выбрано: {serial}"

        self.statusBar().showMessage(text)

    # ---------- Actions ----------
    def launch(self):
        deeplink = self.deeplink_input.text().strip()
        if not deeplink:
            QMessageBox.warning(self, "Ошибка", "Введите диплинк")
            return

        if not self.adb_path:
            QMessageBox.critical(
                self,
                "ADB не найден",
                "adb не найден в системе.\n\n"
                "Установите Android platform-tools и добавьте adb в PATH.",
            )
            return

        if not self.devices:
            QMessageBox.warning(
                self,
                "Устройство не выбрано",
                "Подключите устройство и обновите список.",
            )
            return

        try:
            run_deeplink(self.current_device(), deeplink)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка ADB", str(e))
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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.data["favorites"][row]
            self.favorites_list.takeItem(row)
            save_data(self.data)

    def clear_favorite(self):
        reply = QMessageBox.question(
            self,
            "Удалить",
            "Удалить все диплинки из избранного?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.data["history"].clear()
            self.history_list.clear()
            save_data(self.data)

    def fill_from_history(self, item):
        self.deeplink_input.setText(item.text())

    def launch_from_history(self, item):
        self.deeplink_input.setText(item.text())
        self.launch()

    def launch_from_favorite(self, item):
        row = self.favorites_list.row(item)
        if row < 0:
            return
        self.deeplink_input.setText(self.data["favorites"][row]["deeplink"])
        self.launch()

    def fill_from_favorite(self, item):
        row = self.favorites_list.row(item)
        if row < 0:
            return
        self.deeplink_input.setText(self.data["favorites"][row]["deeplink"])

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
def main():
    app = QApplication(sys.argv)
    apply_theme(app)

    window = DeeplinkLauncher()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
