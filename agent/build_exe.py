import subprocess
import sys

def build_exe():
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--name", "risk_agent",
        "--hidden-import=psutil",
        "main.py",
    ]

    subprocess.run(command, check=True)

if __name__ == "__main__":
    build_exe()