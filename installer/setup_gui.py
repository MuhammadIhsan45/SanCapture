"""
SanCapture Setup Wizard
Modern, standalone Windows Installer for SanCapture.
"""

import sys
import os
import shutil
import zipfile
import winreg
import tempfile
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog, QCheckBox,
    QProgressBar, QMessageBox, QWidget, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap, QIcon

def create_windows_shortcut(target_path: Path, link_path: Path, icon_path: Path = None, description: str = "SanCapture"):
    """Creates a Windows .lnk shortcut using VBScript."""
    link_path.parent.mkdir(parents=True, exist_ok=True)
    vbs_content = f'''Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{str(link_path)}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{str(target_path)}"
oLink.WorkingDirectory = "{str(target_path.parent)}"
oLink.Description = "{description}"
'''
    if icon_path and icon_path.exists():
        vbs_content += f'oLink.IconLocation = "{str(icon_path)}, 0"\n'
    vbs_content += 'oLink.Save\n'

    temp_vbs = Path(tempfile.gettempdir()) / f"mk_sc_{os.getpid()}_{hash(str(link_path)) & 0xffff}.vbs"
    with open(temp_vbs, "w", encoding="utf-8") as f:
        f.write(vbs_content)

    try:
        subprocess.run(["wscript.exe", "//nologo", str(temp_vbs)], check=True, creationflags=0x08000000)
    finally:
        if temp_vbs.exists():
            try:
                temp_vbs.unlink()
            except Exception:
                pass

def get_default_install_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        return Path(local_app_data) / "Programs" / "SanCapture"
    return Path.home() / "AppData" / "Local" / "Programs" / "SanCapture"

class InstallWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, target_dir: Path, create_desktop: bool, create_startmenu: bool, startup_launch: bool):
        super().__init__()
        self.target_dir = target_dir
        self.create_desktop = create_desktop
        self.create_startmenu = create_startmenu
        self.startup_launch = startup_launch

    def run(self):
        try:
            self.progress.emit(10, "Preparing installation directory...")
            self.target_dir.mkdir(parents=True, exist_ok=True)

            # 1. Locate payload zip
            if getattr(sys, 'frozen', False):
                base_path = Path(sys._MEIPASS)
            else:
                base_path = Path(__file__).resolve().parent

            payload_zip = base_path / "payload.zip"
            if not payload_zip.exists():
                # Fallback: check next to executable
                payload_zip = Path(sys.executable).parent / "payload.zip"

            if not payload_zip.exists():
                raise FileNotFoundError(f"Installation payload not found: {payload_zip}")

            self.progress.emit(25, "Extracting SanCapture application files...")
            with zipfile.ZipFile(payload_zip, 'r') as zf:
                total_files = len(zf.namelist())
                for i, file_info in enumerate(zf.infolist()):
                    zf.extract(file_info, self.target_dir)
                    if i % 10 == 0:
                        pct = 25 + int((i / max(1, total_files)) * 45)
                        self.progress.emit(pct, f"Extracting {file_info.filename}...")

            exe_path = self.target_dir / "SanCapture.exe"
            icon_path = self.target_dir / "assets" / "app_icon.ico"
            if not icon_path.exists():
                icon_path = exe_path

            self.progress.emit(75, "Creating shortcuts...")
            # 2. Desktop Shortcut
            if self.create_desktop:
                user_profile = Path(os.environ.get("USERPROFILE", str(Path.home())))
                desktop_lnk = user_profile / "Desktop" / "SanCapture.lnk"
                create_windows_shortcut(exe_path, desktop_lnk, icon_path, "SanCapture - Screenshot & Annotation Studio")

            # 3. Start Menu Shortcut
            if self.create_startmenu:
                appdata = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
                start_menu_dir = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "SanCapture"
                start_menu_lnk = start_menu_dir / "SanCapture.lnk"
                create_windows_shortcut(exe_path, start_menu_lnk, icon_path, "SanCapture - Screenshot & Annotation Studio")
                
                # Uninstaller shortcut in Start Menu
                uninst_exe = self.target_dir / "uninstall.exe"
                if uninst_exe.exists():
                    uninst_lnk = start_menu_dir / "Uninstall SanCapture.lnk"
                    create_windows_shortcut(uninst_exe, uninst_lnk, None, "Uninstall SanCapture")

            self.progress.emit(88, "Registering application in Windows...")
            # 4. Windows Add/Remove Programs Registry
            try:
                reg_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\SanCapture"
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path)
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "SanCapture")
                winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.0.0")
                winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "SanCapture Studio")
                winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(self.target_dir))
                winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(exe_path))
                
                uninst_exe = self.target_dir / "uninstall.exe"
                if uninst_exe.exists():
                    winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{str(uninst_exe)}"')
                winreg.CloseKey(key)
            except Exception as e:
                print("Registry registration warning:", e)

            # 5. Startup Registry
            if self.startup_launch:
                try:
                    run_key = winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion\Run",
                        0, winreg.KEY_SET_VALUE
                    )
                    winreg.SetValueEx(run_key, "SanCapture", 0, winreg.REG_SZ, f'"{str(exe_path)}"')
                    winreg.CloseKey(run_key)
                except Exception as e:
                    print("Startup registration warning:", e)

            self.progress.emit(100, "Installation completed successfully!")
            self.finished.emit(True, "Installation complete.")
        except Exception as e:
            self.finished.emit(False, str(e))

class SetupWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SanCapture Setup Wizard")
        self.setFixedSize(580, 420)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        
        # Style
        self.setStyleSheet("""
            QWizard {
                background-color: #1E2227;
                color: #ECEFF4;
            }
            QWidget {
                background-color: #1E2227;
                color: #ECEFF4;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #D8DEE9;
            }
            QLineEdit {
                background-color: #181A1F;
                color: #FFFFFF;
                border: 1px solid #3E4451;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #61AFEF;
            }
            QPushButton {
                background-color: #282C34;
                color: #ECEFF4;
                border: 1px solid #3E4451;
                border-radius: 4px;
                padding: 6px 18px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #353B45;
                border-color: #61AFEF;
            }
            QCheckBox {
                color: #ECEFF4;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #3E4451;
                border-radius: 3px;
                background-color: #181A1F;
            }
            QCheckBox::indicator:checked {
                background-color: #2563EB;
                border-color: #60A5FA;
            }
            QProgressBar {
                border: 1px solid #3E4451;
                border-radius: 4px;
                background-color: #181A1F;
                text-align: center;
                color: #FFFFFF;
                font-weight: bold;
                height: 22px;
            }
            QProgressBar::chunk {
                background-color: #2563EB;
                border-radius: 3px;
            }
        """)

        # Set Icon
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys._MEIPASS)
        else:
            base_dir = Path(__file__).resolve().parent.parent / "assets"
        
        icon_file = base_dir / "app_icon.ico"
        if not icon_file.exists():
            icon_file = base_dir / "app_icon.png"
        if icon_file.exists():
            self.setWindowIcon(QIcon(str(icon_file)))

        self.install_dir = get_default_install_dir()
        self.launch_app_on_finish = True

        # Add Pages
        self.page_welcome = self._create_welcome_page()
        self.page_progress = self._create_progress_page()
        self.page_finish = self._create_finish_page()

        self.addPage(self.page_welcome)
        self.addPage(self.page_progress)
        self.addPage(self.page_finish)

    def _create_welcome_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Welcome to SanCapture Setup")
        page.setSubTitle("Choose installation location and options for SanCapture.")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(14)

        # Header intro
        lbl_intro = QLabel(
            "This wizard will install <b>SanCapture v1.0.0</b> on your computer.<br>"
            "SanCapture provides high-definition screenshot captures, multi-image batch tools, and annotation studio."
        )
        lbl_intro.setWordWrap(True)
        layout.addWidget(lbl_intro)

        # Directory Selector
        lbl_dir = QLabel("<b>Destination Folder:</b>")
        layout.addWidget(lbl_dir)

        h_dir = QHBoxLayout()
        self.txt_dir = QLineEdit(str(self.install_dir))
        h_dir.addWidget(self.txt_dir)

        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_dir)
        h_dir.addWidget(btn_browse)
        layout.addLayout(h_dir)

        # Options Checkboxes
        lbl_opts = QLabel("<b>Installation Options:</b>")
        layout.addWidget(lbl_opts)

        self.chk_desktop = QCheckBox("Create Desktop shortcut")
        self.chk_desktop.setChecked(True)
        layout.addWidget(self.chk_desktop)

        self.chk_startmenu = QCheckBox("Create Start Menu shortcut")
        self.chk_startmenu.setChecked(True)
        layout.addWidget(self.chk_startmenu)

        self.chk_startup = QCheckBox("Start SanCapture automatically when Windows starts")
        self.chk_startup.setChecked(False)
        layout.addWidget(self.chk_startup)

        layout.addStretch()
        return page

    def _browse_dir(self):
        chosen = QFileDialog.getExistingDirectory(self, "Select Installation Folder", self.txt_dir.text())
        if chosen:
            self.txt_dir.setText(os.path.join(chosen, "SanCapture") if not chosen.endswith("SanCapture") else chosen)

    def _create_progress_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Installing SanCapture")
        page.setSubTitle("Please wait while SanCapture is being installed...")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 20, 10, 10)
        layout.setSpacing(16)

        self.lbl_status = QLabel("Preparing...")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        layout.addStretch()
        return page

    def _create_finish_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Completing SanCapture Setup")
        page.setSubTitle("SanCapture has been successfully installed on your computer.")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(14)

        lbl_done = QLabel(
            "<b>SanCapture Setup is Complete!</b><br><br>"
            "Click Finish to exit setup and start capturing."
        )
        lbl_done.setWordWrap(True)
        layout.addWidget(lbl_done)

        self.chk_run_now = QCheckBox("Launch SanCapture now")
        self.chk_run_now.setChecked(True)
        layout.addWidget(self.chk_run_now)

        layout.addStretch()
        return page

    def initializePage(self, page_id: int):
        if page_id == 1: # Progress page
            self.button(QWizard.WizardButton.BackButton).setEnabled(False)
            self.button(QWizard.WizardButton.NextButton).setEnabled(False)
            self.button(QWizard.WizardButton.CancelButton).setEnabled(False)
            
            target_path = Path(self.txt_dir.text().strip())
            self.install_dir = target_path

            self.worker = InstallWorker(
                target_dir=target_path,
                create_desktop=self.chk_desktop.isChecked(),
                create_startmenu=self.chk_startmenu.isChecked(),
                startup_launch=self.chk_startup.isChecked()
            )
            self.worker.progress.connect(self._on_install_progress)
            self.worker.finished.connect(self._on_install_finished)
            self.worker.start()

    def _on_install_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(msg)

    def _on_install_finished(self, success: bool, msg: str):
        if success:
            self.next()
        else:
            QMessageBox.critical(self, "Installation Error", f"Installation failed:\n{msg}")
            self.reject()

    def accept(self):
        if self.chk_run_now.isChecked():
            exe_path = self.install_dir / "SanCapture.exe"
            if exe_path.exists():
                subprocess.Popen([str(exe_path)], cwd=str(self.install_dir))
        super().accept()

def main():
    app = QApplication(sys.argv)
    wizard = SetupWizard()
    wizard.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
