import os
import subprocess
import sys
import shutil

def build_backend():
    print("Building backend sidecar...")
    backend_dir = os.path.join(os.getcwd(), "backend")
    dist_dir = os.path.join(os.getcwd(), "desktop", "src-tauri", "sidecars")
    os.makedirs(dist_dir, exist_ok=True)

    # Detect platform for sidecar naming (tauri requirement: name-triple)
    # For Windows: name-x86_64-pc-windows-msvc.exe
    target_triple = "x86_64-pc-windows-msvc" # Assuming x64 for now
    sidecar_name = f"backend-sidecar-{target_triple}.exe"

    print(f"Targeting {sidecar_name}")

    # Use PyInstaller to bundle the backend
    # We include app, models, etc.
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name", sidecar_name.replace(".exe", ""),
        "--add-data", "app;app",
        "--add-data", "models;models",
        "--collect-all", "fastapi",
        "--collect-all", "uvicorn",
        "--collect-all", "app",
        "--collect-all", "passlib",
        "--collect-all", "grpc",
        "--collect-all", "boto3",
        "--collect-all", "celery",
        "--hidden-import", "fakeredis.aioredis",
        "--hidden-import", "jwt",
        "--hidden-import", "passlib.handlers.argon2",
        "--hidden-import", "passlib.handlers.bcrypt",
        "--hidden-import", "multipart",
        "desktop_entry.py"
    ]

    subprocess.run(cmd, cwd=backend_dir, check=True, shell=True)

    # Move to sidecars directory
    src = os.path.join(backend_dir, "dist", sidecar_name)
    dst = os.path.join(dist_dir, sidecar_name)
    shutil.copy2(src, dst)
    print(f"Backend sidecar built and moved to {dst}")

def build_frontend():
    print("Building frontend...")
    ui_dir = os.path.join(os.getcwd(), "ui", "react-app")
    subprocess.run(["npm", "install", "--legacy-peer-deps"], cwd=ui_dir, check=True, shell=True)
    subprocess.run(["npm", "run", "build"], cwd=ui_dir, check=True, shell=True)
    print("Frontend built successfully.")

def build_tauri():
    print("Building Tauri app...")
    desktop_dir = os.path.join(os.getcwd(), "desktop")
    # For production build
    subprocess.run(["npx", "tauri", "build"], cwd=desktop_dir, check=True, shell=True)
    print("Tauri app built successfully.")

if __name__ == "__main__":
    try:
        # build_frontend() # Skipped for faster backend iteration
        build_backend()
        # build_tauri() # Skip tauri build in this script for now, let user run it
        print("\nSUCCESS: Desktop components prepared.")
        print("Run 'cd desktop && npx tauri dev' to start in development mode.")
        print("Run 'cd desktop && npx tauri build' to create the installer.")
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
