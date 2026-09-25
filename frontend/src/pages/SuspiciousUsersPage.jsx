import { useEffect, useMemo, useState } from "react";

import { getSuspiciousUsers } from "../api/riskApi.js";
import SuspiciousUserTable from "../components/SuspiciousUserTable.jsx";


function SuspiciousUsersPage() {
  const [users, setUsers] = useState([]);

  const [keyword, setKeyword] = useState("");
  const [riskLevel, setRiskLevel] = useState("ALL");
  const [sortOrder, setSortOrder] = useState("DESC");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // 선택한 의심 사용자
  const [selectedUser, setSelectedUser] = useState(null);


  /**
   * 의심 사용자 목록 조회
   */
  useEffect(() => {
    const fetchSuspiciousUsers = async () => {
      setLoading(true);
      setError("");

      try {
        const data = await getSuspiciousUsers();

        if (!Array.isArray(data)) {
          throw new Error(
            "의심 사용자 응답 형식이 올바르지 않습니다."
          );
        }

        // 백엔드 snake_case -> 프론트 camelCase
        const formattedUsers = data.map((user) => ({
          id: user.id,

          userId: user.user_id,
          sessionId: user.session_id,
          deviceId: user.device_id,

          behaviorScore:
            user.behavior_score ?? null,

          identityScore:
            user.identity_score ?? null,

          riskScore:
            user.risk_score ?? null,

          riskLevel:
            user.risk_level ?? null,

          baselineStatus:
            user.baseline_status ?? null,

          lastDetectedAt:
            user.created_at,

          // 기존 탐지 결과
          detectAnomaly:
            user.detect_anomaly ?? false,

          profileDeviationScore:
            user.profile_deviation_score ?? null,

          newDevice:
            user.new_device ??
            user.is_new_device ??
            false,

          locationChanged:
            user.location_changed ?? false,

          typingAnomaly:
            user.typing_anomaly ?? false,

          mouseAnomaly:
            user.mouse_anomaly ?? false,

          // 신규 reasons 배열
          reasons:
            Array.isArray(user.reasons)
              ? user.reasons
              : [],
        }));

        setUsers(formattedUsers);

      } catch (requestError) {
        console.error(
          "의심 사용자 조회 오류:",
          requestError
        );

        setUsers([]);

        setError(
          requestError.message ||
          "백엔드 서버에서 의심 사용자 목록을 불러오지 못했습니다."
        );

      } finally {
        setLoading(false);
      }
    };

    fetchSuspiciousUsers();
  }, []);


  /**
   * 검색 / 필터 / 정렬
   */
  const filteredUsers = useMemo(() => {
    const searchKeyword =
      keyword.trim().toLowerCase();

    return [...users]
      .filter((user) => {
        const userId = String(
          user.userId ?? ""
        ).toLowerCase();

        const matchesKeyword =
          searchKeyword === "" ||
          userId.includes(searchKeyword);

        const matchesRiskLevel =
          riskLevel === "ALL" ||
          user.riskLevel === riskLevel;

        return (
          matchesKeyword &&
          matchesRiskLevel
        );
      })
      .sort((a, b) => {
        const firstScore =
          Number(a.riskScore ?? 0);

        const secondScore =
          Number(b.riskScore ?? 0);

        if (sortOrder === "ASC") {
          return firstScore - secondScore;
        }

        return secondScore - firstScore;
      });

  }, [
    users,
    keyword,
    riskLevel,
    sortOrder
  ]);


  /**
   * 사용자 선택
   */
  const handleUserSelect = (user) => {
    setSelectedUser(user);
  };


  return (
    <main className="page-container">

      {/* 페이지 상단 */}
      <div className="page-header">
        <div>
          <h1 className="page-title">
            의심 사용자 목록
          </h1>

          <p className="page-description">
            Behavior / Identity 위험도와
            탐지 사유를 기준으로 의심 사용자를 확인합니다.
          </p>
        </div>
      </div>


      {/* 오류 */}
      {error && (
        <p className="error-message">
          {error}
        </p>
      )}


      {/* 필터 */}
      <section className="filter-panel">

        <label>
          <span>
            사용자 검색
          </span>

          <input
            type="search"
            value={keyword}
            placeholder="사용자 ID 입력"
            onChange={(event) =>
              setKeyword(event.target.value)
            }
          />
        </label>


        <label>
          <span>
            위험 등급
          </span>

          <select
            value={riskLevel}
            onChange={(event) =>
              setRiskLevel(event.target.value)
            }
          >
            <option value="ALL">
              전체
            </option>

            <option value="LOW">
              정상
            </option>

            <option value="MEDIUM">
              주의
            </option>

            <option value="HIGH">
              위험
            </option>
          </select>
        </label>


        <label>
          <span>
            점수 정렬
          </span>

          <select
            value={sortOrder}
            onChange={(event) =>
              setSortOrder(event.target.value)
            }
          >
            <option value="DESC">
              높은 순
            </option>

            <option value="ASC">
              낮은 순
            </option>
          </select>
        </label>

      </section>


      {/* 결과 요약 */}
      <div className="result-summary">
        <span>
          의심 사용자{" "}
          <strong>
            {filteredUsers.length}
          </strong>
          명
        </span>
      </div>


      {/* 사용자 테이블 */}
      {loading ? (
        <p className="loading-message">
          의심 사용자 목록을 불러오는 중입니다.
        </p>
      ) : (
        <SuspiciousUserTable
          users={filteredUsers}
          onUserSelect={handleUserSelect}
        />
      )}


      {/* 선택 사용자 탐지 상세 */}
      {selectedUser && (
        <section className="event-detail-card">

          <div className="event-detail-header">

            <div>
              <h2>
                의심 사용자 탐지 상세
              </h2>

              <p>
                해당 사용자가 의심 사용자로
                분류된 원인을 확인합니다.
              </p>
            </div>

            <button
              type="button"
              className="secondary-button"
              onClick={() =>
                setSelectedUser(null)
              }
            >
              닫기
            </button>

          </div>


          <div className="event-detail-grid">

            {/* 사용자 ID */}
            <div className="event-detail-item">
              <span>
                사용자 ID
              </span>

              <strong>
                {selectedUser.userId ?? "-"}
              </strong>
            </div>


            {/* Session ID */}
            <div className="event-detail-item">
              <span>
                Session ID
              </span>

              <strong>
                {selectedUser.sessionId ?? "-"}
              </strong>
            </div>


            {/* 장치 */}
            <div className="event-detail-item">
              <span>
                장치
              </span>

              <strong>
                {selectedUser.deviceId ?? "-"}
              </strong>
            </div>


            {/* Baseline 상태 */}
            <div className="event-detail-item">
              <span>
                Baseline 상태
              </span>

              <strong>
                {selectedUser.baselineStatus ?? "-"}
              </strong>
            </div>


            {/* Behavior Score */}
            <div className="event-detail-item">
              <span>
                Behavior Score
              </span>

              <strong>
                {selectedUser.behaviorScore ?? "-"}
              </strong>
            </div>


            {/* Identity Score */}
            <div className="event-detail-item">
              <span>
                Identity Score
              </span>

              <strong>
                {selectedUser.identityScore ?? "-"}
              </strong>
            </div>


            {/* Risk Score */}
            <div className="event-detail-item">
              <span>
                Risk Score
              </span>

              <strong>
                {selectedUser.riskScore ?? "-"}
              </strong>
            </div>


            {/* Risk Level */}
            <div className="event-detail-item">
              <span>
                Risk Level
              </span>

              <strong>
                {selectedUser.riskLevel ?? "-"}
              </strong>
            </div>


            {/* 프로필 차이 */}
            <div className="event-detail-item">
              <span>
                프로필 편차 점수
              </span>

              <strong>
                {
                  selectedUser
                    .profileDeviationScore ??
                  "-"
                }
              </strong>
            </div>


            {/* ML 이상 */}
            <div className="event-detail-item">
              <span>
                ML 이상 탐지
              </span>

              <strong>
                {
                  selectedUser.detectAnomaly
                    ? "이상"
                    : "정상"
                }
              </strong>
            </div>


            {/* 마지막 탐지 시간 */}
            <div className="event-detail-item">
              <span>
                마지막 탐지 시간
              </span>

              <strong>
                {selectedUser.lastDetectedAt
                  ? new Date(
                      selectedUser.lastDetectedAt
                    ).toLocaleString()
                  : "-"
                }
              </strong>
            </div>

          </div>


          {/* 탐지 사유 */}
          <div className="detection-reason-section">

            <h3>
              탐지 사유
            </h3>

            {selectedUser.reasons.length > 0 ? (

              <ul>
                {selectedUser.reasons.map(
                  (reason, index) => (
                    <li
                      key={
                        reason.reason_code ??
                        index
                      }
                    >
                      <strong>
                        {reason.reason_code ??
                          "UNKNOWN"}
                      </strong>

                      {reason.description && (
                        <>
                          {" - "}
                          {reason.description}
                        </>
                      )}

                      {reason.score_contribution != null && (
                        <>
                          {" "}
                          (+
                          {reason.score_contribution})
                        </>
                      )}
                    </li>
                  )
                )}
              </ul>

            ) : (

              <ul>

                {selectedUser.newDevice && (
                  <li>
                    새로운 장치에서 접근
                  </li>
                )}

                {selectedUser.locationChanged && (
                  <li>
                    평소와 다른 위치에서 접근
                  </li>
                )}

                {selectedUser.typingAnomaly && (
                  <li>
                    평소와 다른 타이핑 패턴
                  </li>
                )}

                {selectedUser.mouseAnomaly && (
                  <li>
                    평소와 다른 마우스 행동
                  </li>
                )}

                {selectedUser.detectAnomaly && (
                  <li>
                    One-Class SVM 이상 탐지
                  </li>
                )}

                {!selectedUser.newDevice &&
                  !selectedUser.locationChanged &&
                  !selectedUser.typingAnomaly &&
                  !selectedUser.mouseAnomaly &&
                  !selectedUser.detectAnomaly && (
                    <li>
                      상세 탐지 사유 정보가 없습니다.
                    </li>
                  )}

              </ul>
            )}

          </div>

        </section>
      )}

    </main>
  );
}


export default SuspiciousUsersPage;