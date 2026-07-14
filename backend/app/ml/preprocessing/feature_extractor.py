import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "datasets"

KEYSTROKE_PATH = DATASET_DIR / "keystroke_dataset.csv"
MERGED_PATH = DATASET_DIR / "merged_dataset.csv"

ESC_KEY_CODE = 27

MAX_IDLE_TIME = 3000
MAX_SESSION_GAP = 10000

MIN_HOLD_TIME = 20
MAX_HOLD_TIME = 1000

MIN_FLIGHT_TIME = 0
MAX_FLIGHT_TIME = 3000

MIN_SESSION_EVENTS = 6

WINDOW_DOWN_COUNT = 20
STEP_DOWN_COUNT = 10


def calculate_session_features(session_df):
    session_df = session_df.sort_values("Time").reset_index(drop=True)

    hold_times = []
    flight_times = []

    key_down_times = {}
    last_up_time = None
    down_count = 0

    for _, row in session_df.iterrows():
        key = row["key"]
        event = str(row["keyEvent"]).lower()
        time = row["Time"]

        if event == "down":
            down_count += 1

            if last_up_time is not None:
                flight_time = time - last_up_time

                if MIN_FLIGHT_TIME <= flight_time <= MAX_FLIGHT_TIME:
                    flight_times.append(flight_time)

            key_down_times[key] = time

        elif event == "up":
            if key in key_down_times:
                hold_time = time - key_down_times[key]

                if MIN_HOLD_TIME <= hold_time <= MAX_HOLD_TIME:
                    hold_times.append(hold_time)

                del key_down_times[key]

            last_up_time = time

    active_time = 0

    for i in range(1, len(session_df)):
        gap = session_df.loc[i, "Time"] - session_df.loc[i - 1, "Time"]

        if 0 <= gap <= MAX_IDLE_TIME:
            active_time += gap

    typing_speed = down_count / (active_time / 1000) if active_time > 0 else 0
    avg_hold_time = sum(hold_times) / len(hold_times) if hold_times else 0
    avg_flight_time = sum(flight_times) / len(flight_times) if flight_times else 0

    return {
        "typing_speed": round(typing_speed, 2),
        "avg_hold_time": round(avg_hold_time, 2),
        "avg_flight_time": round(avg_flight_time, 2),
        "total_keystrokes": down_count
    }


def split_sessions(user_df):
    sessions = []
    current_session = []
    previous_time = None

    for _, row in user_df.iterrows():
        current_time = row["Time"]

        if previous_time is not None:
            gap = current_time - previous_time

            if gap > MAX_SESSION_GAP and current_session:
                sessions.append(pd.DataFrame(current_session))
                current_session = []

        current_session.append(row)

        if row["key"] == ESC_KEY_CODE and str(row["keyEvent"]).lower() == "down":
            sessions.append(pd.DataFrame(current_session))
            current_session = []

        previous_time = current_time

    if current_session:
        sessions.append(pd.DataFrame(current_session))

    return sessions


def split_session_into_windows(session_df):
    session_df = session_df.sort_values("Time").reset_index(drop=True)

    down_indices = session_df[
        session_df["keyEvent"].str.lower() == "down"
    ].index.tolist()

    if len(down_indices) < WINDOW_DOWN_COUNT:
        return [session_df]

    windows = []
    start_pos = 0

    while start_pos + WINDOW_DOWN_COUNT <= len(down_indices):
        start_index = down_indices[start_pos]
        end_index = down_indices[start_pos + WINDOW_DOWN_COUNT - 1]

        window_df = session_df.loc[start_index:end_index].copy()

        if len(window_df) >= MIN_SESSION_EVENTS:
            windows.append(window_df)

        start_pos += STEP_DOWN_COUNT

    return windows


def extract_keystroke_features(input_path=KEYSTROKE_PATH, output_path=MERGED_PATH):
    df = pd.read_csv(input_path)

    required_columns = {"user", "key", "keyEvent", "Time"}

    if not required_columns.issubset(df.columns):
        raise ValueError(f"CSV 파일에 필요한 컬럼이 없습니다: {required_columns}")

    df = df.dropna(subset=["user", "key", "keyEvent", "Time"])

    df["key"] = pd.to_numeric(df["key"], errors="coerce")
    df["Time"] = pd.to_numeric(df["Time"], errors="coerce")

    df = df.dropna(subset=["key", "Time"])
    df["key"] = df["key"].astype(int)

    feature_rows = []

    total_sessions = 0
    total_windows = 0

    for user, user_df in df.groupby("user"):
        user_df = user_df.sort_values("Time").reset_index(drop=True)

        sessions = split_sessions(user_df)
        total_sessions += len(sessions)

        for session_df in sessions:
            if len(session_df) < MIN_SESSION_EVENTS:
                continue

            windows = split_session_into_windows(session_df)
            total_windows += len(windows)

            for window_df in windows:
                features = calculate_session_features(window_df)
                features["user"] = user

                if features["typing_speed"] <= 0:
                    continue

                if features["avg_hold_time"] <= 0:
                    continue

                if features["avg_flight_time"] <= 0:
                    continue

                if features["total_keystrokes"] < 3:
                    continue

                feature_rows.append(features)

    feature_df = pd.DataFrame(feature_rows)

    feature_df = feature_df[
        ["user", "typing_speed", "avg_hold_time", "avg_flight_time", "total_keystrokes"]
    ]

    feature_df = feature_df[
        (feature_df["typing_speed"] >= 0.5) &
        (feature_df["typing_speed"] <= 8) &
        (feature_df["avg_hold_time"] >= 50) &
        (feature_df["avg_hold_time"] <= 200) &
        (feature_df["avg_flight_time"] >= 100) &
        (feature_df["avg_flight_time"] <= 1500) &
        (feature_df["total_keystrokes"] >= 7)
    ]

    feature_df.to_csv(output_path, index=False)

    print(f"merged_dataset.csv 생성 완료: {output_path}")
    print(f"ESC 기준 세션 수: {total_sessions}")
    print(f"윈도우 분할 후 샘플 수: {total_windows}")
    print(f"최종 저장 샘플 수: {len(feature_df)}")
    print(feature_df.head())

    return feature_df


def load_features():
    df = pd.read_csv(MERGED_PATH)

    if "user" in df.columns:
        df = df.drop(columns=["user"])

    return df.values


if __name__ == "__main__":
    extract_keystroke_features()