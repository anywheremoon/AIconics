#PyInstaller를 이용하여 Python 프로그램을 exe 파일로 생성함.
import os
import subprocess


def build_exe(): #PyInstaller 실행
    command = [
        "pyinstaller",
        "--onefile",    # 하나의 exe 파일 생성
        "--name",
        "risk_agent",   # exe 이름
        "main.py"
    ]

    print("EXE 생성 중...")

    subprocess.run(command, check=True)

    print("EXE 생성 완료!")
    print("dist 폴더를 확인하세요.")


# 단독 실행
if __name__ == "__main__":
    build_exe()