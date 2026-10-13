"""
SanCapture Uninstaller
Removes installed files, desktop shortcuts, start menu shortcuts, and registry entries.
"""

import sys
import os
import shutil
import winreg
import tempfile
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

class UninstallWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, install_dir: Path):
        super().__init__()
        self.install_dir = install_dir

    def run(self):
        try:
            self.progress.emit(20, "Removing Shortcuts...")
            # 1. Desktop Shortcut
            user_profile = Path(os.environ.get("USERPROFILE", str(Path.home())))
            desktop_lnk = user_profile / "Desktop" / "SanCapture.lnk"
            if desktop_lnk.exists():
                try:
                    desktop_lnk.unlink()
                except Exception:
                    pass

            # 2. Start Menu Shortcut
            appdata = Path(os.environ.get("APPDATA", str(user_profile / "AppData" / "Roaming")))
            start_menu_dir = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "SanCapture"
            start_menu_lnk = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "SanCapture.lnk"
            if start_menu_lnk.exists():
                try:
                    start_menu_lnk.unlink()
                except Exception:
                    pass
            if start_menu_dir.exists():
                try:
                    shutil.rmtree(start_menu_dir, ignore_errors=True)
                except Exception:
                    pass

            self.progress.emit(50, "Removing Windows Registry entries...")
            # 3. Registry Uninstall Entry
            try:
                key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\SanCapture"
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
            except Exception:
                pass

            # 4. Startup Registry Entry
            try:
                run_key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0, winreg.KEY_SET_VALUE
                )
                winreg.DeleteValue(run_key, "SanCapture")
                winreg.CloseKey(run_key)
            except Exception:
                pass

            self.progress.emit(80, "Removing Application Files...")
            # 5. Delete Application Files via self-deleting batch script
            bat_content = f'''@echo off
timeout /t 2 /nobreak > nul
rmdir /s /q "{str(self.install_dir)}"
del "%~f0"
'''
            temp_bat = Path(tempfile.gettempdir()) / "sancapture_cleanup.bat"
            with open(temp_bat, "w") as f:
                f.write(bat_content)

            subprocess.Popen(
                ["cmd.exe", "/c", str(temp_bat)],
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
            )

            self.progress.emit(100, "SanCapture was successfully uninstalled.")
            self.finished.emit(True, "SanCapture has been completely removed from your computer.")
        except Exception as e:
            self.finished.emit(False, str(e))

class UninstallerWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Uninstall SanCapture")
        self.setFixedSize(480, 240)
        self.setStyleSheet("""
            QDialog {
                background-color: #1E2227;
                color: #ECEFF4;
            }
            QLabel {
                color: #D8DEE9;
            }
            QPushButton {
                background-color: #282C34;
                color: #ECEFF4;
                border: 1px solid #3E4451;
                border-radius: 5px;
                padding: 6px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #353B45;
                border-color: #61AFEF;
            }
            QPushButton#btn_danger {
                background-color: #E06C75;
                color: #FFFFFF;
                border: none;
            }
            QPushButton#btn_danger:hover {
                background-color: #BE5046;
            }
            QProgressBar {
                border: 1px solid #3E4451;
                border-radius: 4px;
                background-color: #181A1F;
                text-align: center;
                color: #FFFFFF;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #E06C75;
                border-radius: 3px;
            }
        """)

        # Install Dir is the directory containing this uninstaller
        if getattr(sys, 'frozen', False):
            self.install_dir = Path(sys.executable).resolve().parent
        else:
            self.install_dir = Path(__file__).resolve().parent.parent

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Uninstall SanCapture")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(title)

        self.lbl_desc = QLabel(
            f"Are you sure you want to completely remove SanCapture and all of its components from:\n{self.install_dir}?"
        )
        self.lbl_desc.setWordWrap(True)
        layout.addWidget(self.lbl_desc)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        layout.addStretch()

        h_btn = QHBoxLayout()
        h_btn.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.close)
        h_btn.addWidget(self.btn_cancel)

        self.btn_uninstall = QPushButton("Uninstall")
        self.btn_uninstall.setObjectName("btn_danger")
        self.btn_uninstall.clicked.connect(self._start_uninstall)
        h_btn.addWidget(self.btn_uninstall)

        layout.addLayout(h_btn)

    def _start_uninstall(self):
        self.btn_uninstall.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        self.lbl_desc.setText("Uninstalling SanCapture... Please wait.")

        self.worker = UninstallWorker(self.install_dir)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, val: int, msg: str):
        self.progress_bar.setValue(val)
        self.lbl_desc.setText(msg)

    def _on_finished(self, success: bool, msg: str):
        if success:
            QMessageBox.information(self, "Uninstalled", msg)
        else:
            QMessageBox.warning(self, "Uninstall Issue", f"Uninstall completed with warnings:\n{msg}")
        self.accept()

def main():
    app = QApplication(sys.argv)
    dlg = UninstallerWindow()
    dlg.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
