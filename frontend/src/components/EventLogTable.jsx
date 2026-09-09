/**
 * ISO 형식 시간을 한국식 날짜·시간으로 변환한다.
 */
function formatDateTime(value) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}


/**
 * 백엔드 위험 등급을 화면용 한글로 변환한다.
 */
function getRiskLevelLabel(level) {
  const normalizedLevel = String(
    level ?? ""
  ).toUpperCase();

  const riskLevelLabels = {
    LOW: "정상",
    MEDIUM: "주의",
    HIGH: "위험",
  };

  return (
    riskLevelLabels[normalizedLevel] ??
    level ??
    "-"
  );
}


/**
 * 위험 등급에 맞는 CSS 클래스명을 반환한다.
 */
function getRiskLevelClass(level) {
  const normalizedLevel = String(
    level ?? ""
  ).toUpperCase();

  switch (normalizedLevel) {
    case "HIGH":
      return "risk-badge-high";

    case "MEDIUM":
      return "risk-badge-medium";

    case "LOW":
      return "risk-badge-low";

    default:
      return "";
  }
}


/**
 * 탐지 사유를 테이블용 짧은 문자열로 변환한다.
 */
function getReasonSummary(reasons) {
  if (!Array.isArray(reasons) || reasons.length === 0) {
    return "-";
  }

  const labels = reasons
    .slice(0, 2)
    .map((reason) => {
      return (
        reason.reason_code ??
        reason.description ??
        "UNKNOWN"
      );
    });

  if (reasons.length > 2) {
    labels.push(`외 ${reasons.length - 2}건`);
  }

  return labels.join(", ");
}


export default function EventLogTable({
  logs = [],
  loading = false,
  onRowSelect,
  onDelete,
  deletingId = null,
}) {
  if (loading) {
    return (
      <p className="loading-message">
        행동 로그를 불러오는 중입니다.
      </p>
    );
  }

  if (
    !Array.isArray(logs) ||
    logs.length === 0
  ) {
    return (
      <p className="empty-message">
        조회된 행동 로그가 없습니다.
      </p>
    );
  }


  return (
    <div className="table-container">

      <table className="event-log-table">

        <thead>
          <tr>
            <th>발생 시간</th>

            <th>사용자 ID</th>

            <th>Session ID</th>

            <th>기기 ID</th>

            <th>IP 주소</th>

            <th>위치</th>

            <th>타이핑 속도</th>

            <th>평균 누름 시간</th>

            <th>평균 전환 시간</th>

            <th>총 키 입력</th>

            <th>마우스 이동</th>

            <th>클릭 수</th>

            <th>새 기기</th>

            <th>Behavior Score</th>

            <th>Identity Score</th>

            <th>리스크 점수</th>

            <th>위험 등급</th>

            <th>탐지 사유</th>

            <th>관리</th>
          </tr>
        </thead>


        <tbody>

          {logs.map((log) => {

            const eventId = log.id;

            return (
              <tr
                key={eventId}
                onClick={() =>
                  onRowSelect?.(log)
                }
              >

                {/* 발생 시간 */}
                <td>
                  {formatDateTime(
                    log.created_at
                  )}
                </td>


                {/* 사용자 */}
                <td>
                  {log.user_id ?? "-"}
                </td>


                {/* Session */}
                <td>
                  {log.session_id ?? "-"}
                </td>


                {/* 기기 */}
                <td>
                  {log.device_id ?? "-"}
                </td>


                {/* IP */}
                <td>
                  {log.ip_address ?? "-"}
                </td>


                {/* 위치 */}
                <td>
                  {log.location ?? "-"}
                </td>


                {/* 타이핑 */}
                <td>
                  {log.typing_speed ?? "-"}
                </td>


                {/* Hold Time */}
                <td>
                  {log.avg_hold_time ?? "-"}
                </td>


                {/* Flight Time */}
                <td>
                  {log.avg_flight_time ?? "-"}
                </td>


                {/* 키 입력 */}
                <td>
                  {log.total_keystrokes ?? "-"}
                </td>


                {/* 마우스 */}
                <td>
                  {log.mouse_move_count ?? "-"}
                </td>


                {/* 클릭 */}
                <td>
                  {log.click_count ?? "-"}
                </td>


                {/* 새 기기 */}
                <td>
                  {log.is_new_device
                    ? "예"
                    : "아니오"}
                </td>


                {/* Behavior Score */}
                <td>
                  {log.behavior_score ?? "-"}
                </td>


                {/* Identity Score */}
                <td>
                  {log.identity_score ?? "-"}
                </td>


                {/* Risk Score */}
                <td>
                  {log.risk_score ?? "-"}
                </td>


                {/* Risk Level */}
                <td>
                  <span
                    className={
                      `risk-badge ${
                        getRiskLevelClass(
                          log.risk_level
                        )
                      }`
                    }
                  >
                    {getRiskLevelLabel(
                      log.risk_level
                    )}
                  </span>
                </td>


                {/* 탐지 사유 */}
                <td>
                  <span
                    title={
                      Array.isArray(log.reasons)
                        ? log.reasons
                            .map(
                              (reason) =>
                                reason.description ??
                                reason.reason_code ??
                                ""
                            )
                            .filter(Boolean)
                            .join("\n")
                        : ""
                    }
                  >
                    {getReasonSummary(
                      log.reasons
                    )}
                  </span>
                </td>


                {/* 삭제 */}
                <td>
                  <button
                    type="button"
                    className="delete-button"
                    disabled={
                      deletingId === eventId
                    }
                    onClick={(event) => {
                      event.stopPropagation();

                      onDelete?.(log);
                    }}
                  >
                    {deletingId === eventId
                      ? "삭제 중..."
                      : "삭제"}
                  </button>
                </td>

              </tr>
            );
          })}

        </tbody>

      </table>

    </div>
  );
}