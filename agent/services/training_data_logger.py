import csv
import math
import threading
from datetime import datetime, timezone
from pathlib import Path


AGENT_DIR = Path(__file__).resolve().parent.parent

DATASET_PATH = (
    AGENT_DIR
    / "datasets"
    / "keyboard_mouse_dataset.csv"
)

FEATURE_NAMES = [
    "typing_speed",
    "avg_hold_time",
    "avg_flight_time",
    "total_keystrokes",
    "mouse_move_count",
    "mouse_move_distance",
    "click_count",
]

# 앞의 두 컬럼은 기록 정보이며 모델 입력에는 사용하지 않음
FIELD_NAMES = [
    "recorded_at",
    "collection_duration_seconds",
    *FEATURE_NAMES,
]

COUNT_FEATURES = {
    "total_keystrokes",
    "mouse_move_count",
    "click_count",
}

_write_lock = threading.Lock()


def save_training_sample(
    behavior_data: dict,
    duration: float,
) -> Path:
    """한 수집 구간의 키보드·마우스 값을 CSV 한 행으로 저장한다."""

    duration = float(duration)

    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("수집 시간은 유한한 양수여야 합니다.")

    row = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        # 설정한 수집 시간이며 정밀 측정한 실제 경과 시간은 아님
        "collection_duration_seconds": duration,
    }

    for name in FEATURE_NAMES:
        value = behavior_data.get(name)

        # 수집 실패를 0으로 숨기지 않음
        if value is None or isinstance(value, bool):
            raise ValueError(f"유효한 학습 Feature가 없습니다: {name}")

        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError(
                f"{name} 값은 숫자여야 합니다."
            ) from error

        if not math.isfinite(number) or number < 0:
            raise ValueError(
                f"{name} 값은 유한한 0 이상의 숫자여야 합니다."
            )

        if name in COUNT_FEATURES:
            if not number.is_integer():
                raise ValueError(f"{name} 값은 정수여야 합니다.")

            row[name] = int(number)
        else:
            row[name] = number

    with _write_lock:
        DATASET_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        has_content = (
            DATASET_PATH.exists()
            and DATASET_PATH.stat().st_size > 0
        )

        # 다른 형식의 CSV에 잘못 이어 쓰는 것을 방지
        if has_content:
            with DATASET_PATH.open(
                "r",
                newline="",
                encoding="utf-8",
            ) as file:
                existing_header = next(csv.reader(file), None)

            if existing_header != FIELD_NAMES:
                raise ValueError(
                    "기존 학습 CSV의 컬럼 구성이 다릅니다. "
                    "기존 파일을 별도 보관한 뒤 다시 실행하세요."
                )

        with DATASET_PATH.open(
            "a",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=FIELD_NAMES,
            )

            if not has_content:
                writer.writeheader()

            writer.writerow(row)

    return DATASET_PATH