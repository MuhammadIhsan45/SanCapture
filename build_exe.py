"""
Build Script for compiling SanCapture into standalone .exe with PyInstaller.
"""

import os
import sys
import subprocess
from pathlib import Path
from PIL import Image, ImageEnhance

def generate_app_icon(output_path: Path):
    """Generates a crisp, professional multi-size Windows .ico file from master PNG."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    png_source = output_path.parent / "app_icon.png"
    
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)]
    
    if png_source.exists():
        master = Image.open(png_source).convert("RGBA")
    else:
        master = Image.new("RGBA", (512, 512), (15, 23, 42, 255))
        
    master.save(
        str(output_path),
        format="ICO",
        sizes=sizes
    )
    print(f"[Build] Generated high-definition application icon: {output_path}")

import zipfile
import shutil

def make_payload_zip(src_dir: Path, zip_dest: Path):
    """Zips the onedir application folder into a payload zip."""
    zip_dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_dest, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                abs_file = Path(root) / file
                rel_path = abs_file.relative_to(src_dir)
                zf.write(abs_file, rel_path)
    print(f"[Build] Created installer payload: {zip_dest} ({zip_dest.stat().st_size / 1024 / 1024:.2f} MB)")

def build_executable():
    base_dir = Path(__file__).resolve().parent
    assets_dir = base_dir / "assets"
    icon_file = assets_dir / "app_icon.ico"
    installer_dir = base_dir / "installer"

    # Step 1: Ensure HD icon is generated
    generate_app_icon(icon_file)

    # Step 2: PyInstaller directories
    entrypoint = base_dir / "app" / "main.py"
    dist_dir = base_dir / "dist"
    build_dir = base_dir / "build"
    assets_data = f"{assets_dir};assets"

    # 2a. Build Onedir Distribution
    cmd_dir = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        f"--name=SanCapture",
        f"--icon={icon_file}",
        f"--add-data={assets_data}",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--specpath={base_dir}",
        f"--paths={base_dir}",
        str(entrypoint)
    ]

    print("\n[Build 1/4] Compiling SanCapture (onedir distribution)...")
    res1 = subprocess.run(cmd_dir, cwd=str(base_dir))

    # 2b. Build Uninstaller executable inside onedir folder
    uninstaller_entry = installer_dir / "uninstaller.py"
    cmd_uninst = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        f"--name=uninstall",
        f"--icon={icon_file}",
        f"--distpath={dist_dir / 'SanCapture'}",
        f"--workpath={build_dir}",
        f"--specpath={base_dir}",
        str(uninstaller_entry)
    ]
    print("\n[Build 2/4] Compiling uninstaller...")
    res_u = subprocess.run(cmd_uninst, cwd=str(base_dir))

    # 2c. Package onedir folder into installer payload
    payload_zip = installer_dir / "payload.zip"
    make_payload_zip(dist_dir / "SanCapture", payload_zip)

    # 2d. Build Setup Wizard Installer (.exe)
    setup_entry = installer_dir / "setup_gui.py"
    setup_data = f"{payload_zip};."
    cmd_setup = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        f"--name=SanCapture_Setup",
        f"--icon={icon_file}",
        f"--add-data={setup_data}",
        f"--add-data={assets_data}",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--specpath={base_dir}",
        f"--paths={base_dir}",
        str(setup_entry)
    ]
    print("\n[Build 3/4] Compiling SanCapture_Setup.exe (Installer Wizard)...")
    res_setup = subprocess.run(cmd_setup, cwd=str(base_dir))

    # 2e. Build Onefile Portable
    cmd_file = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        f"--name=SanCapture_Portable",
        f"--icon={icon_file}",
        f"--add-data={assets_data}",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--specpath={base_dir}",
        f"--paths={base_dir}",
        str(entrypoint)
    ]

    print("\n[Build 4/4] Compiling SanCapture_Portable.exe (single-file)...")
    res2 = subprocess.run(cmd_file, cwd=str(base_dir))

    if res1.returncode == 0 and res_setup.returncode == 0 and res2.returncode == 0:
        # Copy setup exe & portable exe to root folder for instant access
        try:
            shutil.copy2(dist_dir / "SanCapture_Setup.exe", base_dir / "SanCapture_Setup.exe")
            shutil.copy2(dist_dir / "SanCapture_Portable.exe", base_dir / "SanCapture.exe")
        except Exception as e:
            print("Copy warning:", e)

        print(f"\n=======================================================")
        print(f"[Build Success] All Distributions Created Successfully!")
        print(f"=======================================================")
        print(f"1. INSTALLER SETUP:  {base_dir / 'SanCapture_Setup.exe'}")
        print(f"2. PORTABLE EXE:     {base_dir / 'SanCapture.exe'}")
        print(f"3. DIST INSTALLER:   {dist_dir / 'SanCapture_Setup.exe'}")
        print(f"4. DIST PORTABLE:    {dist_dir / 'SanCapture_Portable.exe'}")
        print(f"5. DIST STANDALONE:  {dist_dir / 'SanCapture' / 'SanCapture.exe'}")
    else:
        print("\n[Build Warning] One or more builds encountered issues.")

if __name__ == "__main__":
    build_executable()
