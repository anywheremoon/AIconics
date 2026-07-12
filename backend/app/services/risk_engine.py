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

    # 클릭 수 과다 + 10점
    if event_data.click_count > 100:
        score += 10

    return min(score, 100) #최종 점수는 100점이 넘지 않게 함


def get_risk_level(score): #위험 등급
    if score >= 70:
        return "HIGH"
    elif score >= 40:
        return "MEDIUM"
    return "LOW"