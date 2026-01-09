#!/usr/bin/env python3
import json
import os
import subprocess
import sys

from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

DATA_FILE = "deeplinks.json"


# ---------- ADB ----------
def get_devices():
    try:
        result = subprocess.run(
            ["adb", "devices"], capture_output=True, text=True, check=True
        )
        lines = result.stdout.strip().splitlines()[1:]
        return [line.split()[0] for line in lines if "device" in line]
    except Exception:
        return []


def run_deeplink(device, deeplink):
    cmd = ["adb"]
    if device:
        cmd += ["-s", device]

    cmd += ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", deeplink]
    subprocess.run(cmd, check=True)


# ---------- Data ----------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"history": [], "favorites": []}

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------- UI ----------
class DeeplinkLauncher(QWidget):
    def __init__(self):
        super().__init__()

        self.devices = get_devices()
        self.data = load_data()

        self.setWindowTitle("ADB Deeplink Launcher")
        self.setMinimumSize(900, 500)

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Device selector
        if len(self.devices) > 1:
            device_layout = QHBoxLayout()
            device_layout.addWidget(QLabel("Устройство:"))

            self.device_combo = QComboBox()
            self.device_combo.addItems(self.devices)
            device_layout.addWidget(self.device_combo)

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

        fav_btn = QPushButton("⭐ В избранное")
        fav_btn.clicked.connect(self.add_to_favorites)

        rename_btn = QPushButton("✏️ Переименовать")
        rename_btn.clicked.connect(self.rename_favorite)

        delete_btn = QPushButton("🗑 Удалить избранное")
        delete_btn.clicked.connect(self.delete_favorite)

        buttons_layout.addWidget(launch_btn)
        buttons_layout.addWidget(fav_btn)
        buttons_layout.addWidget(rename_btn)
        buttons_layout.addWidget(delete_btn)

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

        clear_history_btn = QPushButton("🧹 Очистить историю")
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

        favorites_layout.addWidget(self.favorites_list)

        lists_layout.addWidget(history_box)
        lists_layout.addWidget(favorites_box)

        main_layout.addLayout(lists_layout)

    # ---------- Actions ----------
    def current_device(self):
        if self.device_combo:
            return self.device_combo.currentText()
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


# ---------- Run ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DeeplinkLauncher()
    window.show()
    sys.exit(app.exec_())
