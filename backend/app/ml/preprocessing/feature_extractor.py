from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "datasets"

KEYSTROKE_PATH = DATASET_DIR / "keystroke_dataset.csv"
MERGED_PATH = DATASET_DIR / "merged_dataset.csv"


# Agent의 SEND_INTERVAL = 30과 동일하게 유지
WINDOW_DURATION_SECONDS = 30
WINDOW_DURATION_MS = WINDOW_DURATION_SECONDS * 1000

# Agent keyboard_collector.py와 동일한 기준
MAX_IDLE_TIME_MS = 3000

MIN_HOLD_TIME_MS = 20
MAX_HOLD_TIME_MS = 1000

MIN_FLIGHT_TIME_MS = 0
MAX_FLIGHT_TIME_MS = 3000

# 학습 샘플에 필요한 최소 입력 수
# 정상/이상을 나누는 기준이 아니라 데이터 부족 제외 기준
MIN_KEYSTROKES = 7

FEATURE_NAMES = [
    "typing_speed",
    "avg_hold_time",
    "avg_flight_time",
    "total_keystrokes",
]


def calculate_session_features(window_df):
    """한 구간의 키보드 Feature를 Agent와 같은 방식으로 계산한다."""
    window_df = window_df.sort_values(
        "Time",
        kind="stable",
    ).reset_index(drop=True)

    press_times = {}
    hold_times = []
    flight_times = []

    total_keystrokes = 0
    last_release_time = None
    previous_event_time = None
    active_time_ms = 0.0

    for row in window_df.itertuples(index=False):
        key = row.key
        event = row.keyEvent
        current_time = float(row.Time)

        # 반복 down을 포함한 모든 down/up 이벤트 간격으로 계산
        if previous_event_time is not None:
            gap_ms = current_time - previous_event_time

            if 0 <= gap_ms <= MAX_IDLE_TIME_MS:
                active_time_ms += gap_ms

        previous_event_time = current_time

        if event == "down":
            # Agent와 동일하게 키 반복 down 제외
            if key in press_times:
                continue

            press_times[key] = current_time
            total_keystrokes += 1

            if last_release_time is not None:
                flight_time_ms = (
                    current_time - last_release_time
                )

                if (
                    MIN_FLIGHT_TIME_MS
                    <= flight_time_ms
                    <= MAX_FLIGHT_TIME_MS
                ):
                    flight_times.append(flight_time_ms)

        elif event == "up":
            if key in press_times:
                press_time = press_times.pop(key)
                hold_time_ms = current_time - press_time

                if (
                    MIN_HOLD_TIME_MS
                    <= hold_time_ms
                    <= MAX_HOLD_TIME_MS
                ):
                    hold_times.append(hold_time_ms)

            last_release_time = current_time

    typing_speed = (
        total_keystrokes / (active_time_ms / 1000)
        if active_time_ms > 0
        else 0.0
    )

    avg_hold_time = (
        sum(hold_times) / len(hold_times)
        if hold_times
        else 0.0
    )

    avg_flight_time = (
        sum(flight_times) / len(flight_times)
        if flight_times
        else 0.0
    )

    return {
        "typing_speed": round(typing_speed, 2),
        "avg_hold_time": round(avg_hold_time, 2),
        "avg_flight_time": round(avg_flight_time, 2),
        "total_keystrokes": total_keystrokes,
    }


def split_into_time_windows(user_df):
    """사용자별 이벤트를 겹치지 않는 30초 구간으로 나눈다."""
    user_df = user_df.sort_values(
        "Time",
        kind="stable",
    ).reset_index(drop=True)

    if user_df.empty:
        return []

    start_time = float(user_df["Time"].iloc[0])

    window_ids = (
        (user_df["Time"] - start_time) // WINDOW_DURATION_MS
    ).astype("int64")

    # 이벤트가 있는 구간만 반환
    # 각 구간의 수집 상태는 calculate_session_features에서 초기화됨
    return [
        window_df.copy()
        for _, window_df in user_df.groupby(
            window_ids,
            sort=True,
        )
    ]


def extract_keystroke_features(
    input_path=KEYSTROKE_PATH,
    output_path=MERGED_PATH,
):
    input_path = Path(input_path)
    output_path = Path(output_path)

    df = pd.read_csv(input_path)

    required_columns = {
        "user",
        "key",
        "keyEvent",
        "Time",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"CSV에 필요한 컬럼이 없습니다: {sorted(missing_columns)}"
        )

    original_count = len(df)

    df = df.dropna(
        subset=["user", "key", "keyEvent", "Time"]
    ).copy()

    df["key"] = pd.to_numeric(
        df["key"],
        errors="coerce",
    )
    df["Time"] = pd.to_numeric(
        df["Time"],
        errors="coerce",
    )

    df[["key", "Time"]] = df[["key", "Time"]].replace(
        [float("inf"), float("-inf")],
        float("nan"),
    )

    df = df.dropna(subset=["key", "Time"]).copy()

    df["keyEvent"] = (
        df["keyEvent"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    df = df[
        df["keyEvent"].isin(["down", "up"])
    ].copy()

    if df.empty:
        raise ValueError("사용할 수 있는 키보드 이벤트가 없습니다.")

    # 정수가 아닌 키 코드는 조용히 잘라내지 않고 오류 처리
    if (df["key"] % 1 != 0).any():
        raise ValueError("key 컬럼에 정수가 아닌 값이 있습니다.")

    df["key"] = df["key"].astype(int)

    feature_rows = []
    total_windows = 0
    skipped_windows = 0

    for user, user_df in df.groupby("user", sort=False):
        windows = split_into_time_windows(user_df)
        total_windows += len(windows)

        for window_df in windows:
            features = calculate_session_features(window_df)

            # 측정값이 부족한 구간은 학습에서 제외
            if (
                features["total_keystrokes"] < MIN_KEYSTROKES
                or features["typing_speed"] <= 0
                or features["avg_hold_time"] <= 0
                or features["avg_flight_time"] <= 0
            ):
                skipped_windows += 1
                continue

            feature_rows.append({
                "user": user,
                **features,
            })

    if not feature_rows:
        raise ValueError(
            "학습 가능한 샘플이 없습니다. "
            "Time 단위와 원본 이벤트를 확인하세요."
        )

    feature_df = pd.DataFrame(
        feature_rows,
        columns=["user", *FEATURE_NAMES],
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    feature_df.to_csv(output_path, index=False)

    print(f"CSV 생성 완료: {output_path}")
    print(f"수집 구간: {WINDOW_DURATION_SECONDS}초")
    print(f"제외한 원본 행 수: {original_count - len(df)}")
    print(f"이벤트가 있는 구간 수: {total_windows}")
    print(f"측정값 부족으로 제외한 구간 수: {skipped_windows}")
    print(f"최종 학습 샘플 수: {len(feature_df)}")
    print(feature_df.head())

    return feature_df


def load_features():
    df = pd.read_csv(MERGED_PATH)
    return df[FEATURE_NAMES].to_numpy()


if __name__ == "__main__":
    extract_keystroke_features()