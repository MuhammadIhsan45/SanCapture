"""
SanCapture - macOS Application and DMG Builder
Compiles SanCapture into a macOS .app bundle and packages it into an installer .dmg.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from PIL import Image

def generate_app_icns(output_path: Path):
    """Generates an Apple ICNS file from the master PNG."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    png_source = output_path.parent / "app_icon.png"
    
    if not png_source.exists():
        print(f"[Build Error] Icon source {png_source} not found!")
        return False
        
    try:
        master = Image.open(png_source).convert("RGBA")
        master.save(str(output_path), format="ICNS")
        print(f"[Build] Successfully generated macOS ICNS icon: {output_path}")
        return True
    except Exception as e:
        print(f"[Build Warning] Could not generate ICNS via Pillow: {e}")
        return False

def build_app_bundle(base_dir: Path, dist_dir: Path, build_dir: Path):
    """Runs PyInstaller to compile SanCapture.app bundle."""
    spec_file = base_dir / "SanCapture_mac.spec"
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        str(spec_file)
    ]
    
    print("\n[Build 1/2] Compiling SanCapture.app bundle with PyInstaller...")
    print(f"Command: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=str(base_dir))
    return res.returncode == 0

def create_dmg_with_hdiutil(app_bundle: Path, dmg_output: Path, vol_name: str = "SanCapture"):
    """
    Creates a clean, native macOS .dmg using built-in hdiutil with /Applications drag-and-drop link.
    Requires no external dependencies.
    """
    staging_dir = dmg_output.parent / "dmg_staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"[DMG] Staging application into {staging_dir}...")
    dest_app = staging_dir / app_bundle.name
    shutil.copytree(app_bundle, dest_app, symlinks=True)
    
    # Create /Applications symlink
    app_link = staging_dir / "Applications"
    try:
        os.symlink("/Applications", app_link)
    except Exception as e:
        # Fallback via ln -s
        subprocess.run(["ln", "-s", "/Applications", str(app_link)], check=False)
        
    # Remove existing DMG if present
    if dmg_output.exists():
        dmg_output.unlink()
        
    print(f"[DMG] Generating compressed DMG with hdiutil: {dmg_output}...")
    cmd = [
        "hdiutil", "create",
        "-volname", vol_name,
        "-srcfolder", str(staging_dir),
        "-ov",
        "-format", "UDZO",
        str(dmg_output)
    ]
    
    res = subprocess.run(cmd, check=False)
    
    # Cleanup staging directory
    try:
        shutil.rmtree(staging_dir)
    except Exception:
        pass
        
    return res.returncode == 0

def create_dmg_with_create_dmg(app_bundle: Path, dmg_output: Path, vol_name: str = "SanCapture"):
    """Creates an aesthetic DMG if create-dmg utility is installed."""
    if dmg_output.exists():
        dmg_output.unlink()
        
    cmd = [
        "create-dmg",
        "--volname", vol_name,
        "--window-pos", "200", "120",
        "--window-size", "640", "420",
        "--icon-size", "100",
        "--icon", app_bundle.name, "180", "180",
        "--app-drop-link", "460", "180",
        "--hide-extension", app_bundle.name,
        str(dmg_output),
        str(app_bundle.parent)
    ]
    res = subprocess.run(cmd, check=False)
    return res.returncode == 0

def build_macos_package():
    base_dir = Path(__file__).resolve().parent
    assets_dir = base_dir / "assets"
    icon_file = assets_dir / "app_icon.icns"
    dist_dir = base_dir / "dist"
    build_dir = base_dir / "build"
    dmg_output = dist_dir / "SanCapture.dmg"

    # Step 1: Ensure ICNS icon is present
    if not icon_file.exists():
        generate_app_icns(icon_file)

    if sys.platform != "darwin":
        print("\n" + "=" * 65)
        print("[Notice] Running on non-macOS host (" + sys.platform + ")")
        print("macOS binaries (.app and .dmg) must be compiled in a macOS environment.")
        print("To build SanCapture.dmg:")
        print("  Option A (Local Mac): Run 'python build_mac.py' or './build_dmg.sh' on macOS.")
        print("  Option B (GitHub Actions): Push to GitHub. The included workflow")
        print("           '.github/workflows/build_macos.yml' will automatically build")
        print("           and release 'SanCapture.dmg' for free using Apple macOS runners!")
        print("=" * 65 + "\n")
        return False

    # Step 2: Build .app bundle
    success = build_app_bundle(base_dir, dist_dir, build_dir)
    if not success:
        print("[Build Error] PyInstaller failed to compile SanCapture.app!")
        return False

    app_bundle = dist_dir / "SanCapture.app"
    if not app_bundle.exists():
        print(f"[Build Error] Bundle not found at {app_bundle}!")
        return False

    print("\n[Build 2/2] Creating DMG installer...")
    
    # Try create-dmg first if available, else native hdiutil
    has_create_dmg = shutil.which("create-dmg") is not None
    dmg_success = False
    
    if has_create_dmg:
        print("[DMG] Using 'create-dmg' utility...")
        dmg_success = create_dmg_with_create_dmg(app_bundle, dmg_output)
        
    if not dmg_success:
        print("[DMG] Using native macOS 'hdiutil'...")
        dmg_success = create_dmg_with_hdiutil(app_bundle, dmg_output)

    if dmg_success and dmg_output.exists():
        dmg_size = dmg_output.stat().st_size / (1024 * 1024)
        print("\n" + "=" * 65)
        print(f"[SUCCESS] macOS DMG Package Created Successfully!")
        print(f"Location: {dmg_output}")
        print(f"Size:     {dmg_size:.2f} MB")
        print("=" * 65 + "\n")
        return True
    else:
        print("[Build Error] Failed to generate DMG installer.")
        return False

if __name__ == "__main__":
    success = build_macos_package()
    sys.exit(0 if success else 1)
