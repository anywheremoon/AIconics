/**
 * ISO 형식 시간을 한국식 날짜·시간으로 변환
 */
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


/**
 * 위험 등급 한글 변환
 */
function getRiskLabel(level) {
  const normalizedLevel = String(
    level ?? ""
  ).toUpperCase();

  if (normalizedLevel === "HIGH") {
    return "위험";
  }

  if (normalizedLevel === "MEDIUM") {
    return "주의";
  }

  if (normalizedLevel === "LOW") {
    return "정상";
  }

  return "-";
}


/**
 * 탐지 사유를 테이블용 짧은 문자열로 변환
 */
function getReasonSummary(reasons) {
  if (
    !Array.isArray(reasons) ||
    reasons.length === 0
  ) {
    return "-";
  }

  const reasonTexts = reasons
    .slice(0, 2)
    .map((reason) => {
      return (
        reason.reason_code ??
        reason.description ??
        "UNKNOWN"
      );
    });

  if (reasons.length > 2) {
    reasonTexts.push(
      `외 ${reasons.length - 2}건`
    );
  }

  return reasonTexts.join(", ");
}


function SuspiciousUserTable({
  users,
  onUserSelect,
}) {
  if (
    !Array.isArray(users) ||
    users.length === 0
  ) {
    return (
      <p className="empty-message">
        의심 사용자가 없습니다.
      </p>
    );
  }

  return (
    <div className="table-container">

      <table className="data-table">

        <thead>
          <tr>
            <th>사용자 ID</th>

            <th>Session ID</th>

            <th>기기 ID</th>

            <th>Behavior Score</th>

            <th>Identity Score</th>

            <th>리스크 점수</th>

            <th>위험 등급</th>

            <th>탐지 사유</th>

            <th>최근 탐지 시간</th>
          </tr>
        </thead>


        <tbody>

          {users.map((user) => {

            const level = String(
              user.riskLevel ?? ""
            ).toLowerCase();

            return (
              <tr
                key={
                  user.id ??
                  `${user.userId}-${user.deviceId}-${user.lastDetectedAt}`
                }
                onClick={() =>
                  onUserSelect?.(user)
                }
                style={{
                  cursor: "pointer",
                }}
              >

                {/* 사용자 ID */}
                <td>
                  {user.userId ?? "-"}
                </td>


                {/* Session ID */}
                <td>
                  {user.sessionId ?? "-"}
                </td>


                {/* 기기 ID */}
                <td>
                  {user.deviceId ?? "-"}
                </td>


                {/* Behavior Score */}
                <td>
                  {user.behaviorScore ?? "-"}
                </td>


                {/* Identity Score */}
                <td>
                  {user.identityScore ?? "-"}
                </td>


                {/* Risk Score */}
                <td>
                  {user.riskScore ?? "-"}
                </td>


                {/* Risk Level */}
                <td>
                  <span
                    className={
                      `risk-badge risk-badge-${level}`
                    }
                  >
                    {getRiskLabel(
                      user.riskLevel
                    )}
                  </span>
                </td>


                {/* 탐지 사유 */}
                <td>
                  <span
                    title={
                      Array.isArray(user.reasons)
                        ? user.reasons
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
                      user.reasons
                    )}
                  </span>
                </td>


                {/* 최근 탐지 시간 */}
                <td>
                  {formatDateTime(
                    user.lastDetectedAt
                  )}
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