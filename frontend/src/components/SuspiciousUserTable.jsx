function formatDateTime(value) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("ko-KR");
}

function getRiskLabel(level) {
  const normalizedLevel = String(level ?? "").toUpperCase();

  if (normalizedLevel === "HIGH") {
    return "위험";
  }

  if (normalizedLevel === "MEDIUM") {
    return "주의";
  }

  return "정상";
}

function SuspiciousUserTable({ users, onUserSelect }) {
  if (!users || users.length === 0) {
    return <p className="empty-message">의심 사용자가 없습니다.</p>;
  }

  return (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>사용자 ID</th>
            <th>기기 ID</th>
            <th>리스크 점수</th>
            <th>위험 등급</th>
            <th>최근 탐지 시간</th>
            <th>상세 보기</th>
          </tr>
        </thead>

        <tbody>
          {users.map((user) => {
            const level = String(user.riskLevel ?? "").toLowerCase();

            return (
              <tr key={`${user.userId}-${user.deviceId}`}>
                <td>{user.userId}</td>
                <td>{user.deviceId}</td>
                <td>{user.riskScore}</td>
                <td>
                  <span className={`risk-badge risk-badge-${level}`}>
                    {getRiskLabel(user.riskLevel)}
                  </span>
                </td>
                <td>{formatDateTime(user.lastDetectedAt)}</td>
                <td>
                  <button
                    type="button"
                    className="action-button"
                    onClick={() => onUserSelect?.(user)}
                  >
                    로그 보기
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

export default SuspiciousUserTable;