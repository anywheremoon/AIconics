from app.services.ml_engine import detect_anomaly


def calculate_risk_score(event_data):

    score = 0

    # 새 기기 +20점
    if event_data.is_new_device:
        score += 20

    # 위치 정보 없음 +15점
    if not event_data.location:
        score += 15

    # 타이핑 속도 이상 +20점
    if event_data.typing_speed < 80 or event_data.typing_speed > 300:
        score += 20

    # 마우스 이동 부족 +10점
    if event_data.mouse_move_count < 50:
        score += 10

    # 클릭 수 과다 +10점
    if event_data.click_count > 100:
        score += 10

    # Pydantic 객체 → dict
    event_dict = event_data.model_dump()

    # ==========================
    # ML 이상 탐지
    # ==========================
    ml_result = detect_anomaly(event_dict)

    print("ML 결과:", ml_result)
    print("ML 반영 전 점수:", score)

    if ml_result["is_anomaly"]:
        score += 30

    print("ML 반영 후 점수:", score)

    # ==========================
    # 최종 점수
    # ==========================
    final_score = min(score, 100)

    return {
        "risk_score": final_score,
        "risk_level": get_risk_level(final_score),
        "is_anomaly": ml_result["is_anomaly"],
        "ml_prediction": ml_result["prediction"],
        "ml_decision_score": ml_result["decision_score"]
    }


def get_risk_level(score):
    if score >= 70:
        return "HIGH"
    elif score >= 40:
        return "MEDIUM"
    return "LOW"