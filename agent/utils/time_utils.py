#시간과 관련된 기능을 수행하는 모듈
from datetime import datetime
import time


def get_timestamp(): # 현재 시간을 ISO 형식 문자열로 반환 예) 2026-07-07T18:30:12
    return datetime.now().isoformat()

def wait_seconds(seconds): # 지정한 시간(초)만큼 프로그램을 대기시킨다. Args: seconds (int): 대기 시간
    time.sleep(seconds)

# 테스트용
if __name__ == "__main__":
    print(get_timestamp())