/**
 * ISO 형식의 시간을 한국 형식으로 변환한다.
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
  const riskLevelLabels = {
    LOW: "정상",
    MEDIUM: "주의",
    HIGH: "위험",
  };

  return riskLevelLabels[level] ?? level ?? "-";
}


/**
 * 위험 등급에 사용할 CSS 클래스명을 반환한다.
 */
function getRiskLevelClass(level) {
  switch (level) {
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


export default function EventLogTable({
  logs = [],
  loading = false,
  onRowSelect,
}) {
  if (loading) {
    return (
      <p className="loading-message">
        행동 로그를 불러오는 중입니다.
      </p>
    );
  }

  if (!Array.isArray(logs) || logs.length === 0) {
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
            <th>리스크 점수</th>
            <th>위험 등급</th>
          </tr>
        </thead>

        <tbody>
          {logs.map((log, index) => {
            /*
             * id가 존재하면 id를 key로 사용한다.
             * id가 없다면 user_id, created_at, index를 조합한다.
             */
            const rowKey =
              log.id ??
              `${log.user_id}-${log.created_at}-${index}`;

            return (
              <tr
                key={rowKey}
                className={
                  onRowSelect ? "clickable-row" : ""
                }
                onClick={() => onRowSelect?.(log)}
              >
                <td>{formatDateTime(log.created_at)}</td>

                <td>{log.user_id ?? "-"}</td>

                <td>{log.device_id ?? "-"}</td>

                <td>{log.ip_address ?? "-"}</td>

                <td>{log.location ?? "-"}</td>

                <td>{log.typing_speed ?? "-"}</td>

                <td>{log.avg_hold_time ?? "-"}</td>

                <td>{log.avg_flight_time ?? "-"}</td>

                <td>{log.total_keystrokes ?? "-"}</td>

                <td>{log.mouse_move_count ?? "-"}</td>

                <td>{log.click_count ?? "-"}</td>

                <td>
                  {log.is_new_device ? "예" : "아니오"}
                </td>

                <td>
                  <strong>{log.risk_score ?? "-"}</strong>
                </td>

                <td>
                  <span
                    className={`risk-badge ${getRiskLevelClass(
                      log.risk_level
                    )}`}
                  >
                    {getRiskLevelLabel(log.risk_level)}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}