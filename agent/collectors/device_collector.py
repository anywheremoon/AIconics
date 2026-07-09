#사용자의 PC(기기) 정보를 수집하는 모듈
import platform
import socket
import uuid
import psutil


def get_device_info():            #현재 사용 중인 PC의 정보를 수집하여 Dictionary 형태로 반환함
   
    # MAC Address를 이용하여 고유한 Device ID 생성
    device_id = str(uuid.getnode())

    # 현재 컴퓨터 이름
    hostname = socket.gethostname()

    # IP 주소 얻기
    try:
        ip_address = socket.gethostbyname(hostname)
    except Exception:
        ip_address = "Unknown"

    # 운영체제 이름
    os_name = platform.system()

    # 운영체제 버전
    os_version = platform.version()

    # CPU 정보
    cpu = platform.processor()

    # 전체 RAM 용량(GB)
    ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 2)

    return {
        "device_id": device_id,
        "ip_address": ip_address,
        "os": os_name,
        "os_version": os_version,
        "cpu": cpu,
        "ram_gb": ram_gb
    }

# 단독 실행 시 테스트
if __name__ == "__main__":
    print(get_device_info())