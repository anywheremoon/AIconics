import { useEffect, useMemo, useState } from "react";

import {
  deleteEventLog,
  getEventLogs,
} from "../api/riskApi";

import EventLogTable from "../components/EventLogTable";


const INITIAL_FILTERS = {
  userId: "",
  riskLevel: "all",
  startDate: "",
  endDate: "",
};


export default function EventLogsPage() {
  const [logs, setLogs] = useState([]);

  const [filters, setFilters] =
    useState(INITIAL_FILTERS);

  const [appliedFilters, setAppliedFilters] =
    useState(INITIAL_FILTERS);

  const [loading, setLoading] = useState(false);

  const [deletingId, setDeletingId] =
    useState(null);

  const [error, setError] = useState("");

  // 선택한 행동 로그
  const [selectedLog, setSelectedLog] =
    useState(null);


  /**
   * 백엔드에서 행동 로그 전체 조회
   */
  async function loadLogs() {
    setLoading(true);
    setError("");

    try {
      const data = await getEventLogs();

      if (Array.isArray(data)) {
        setLogs(data);
      } else {
        setLogs([]);

        setError(
          "행동 로그 응답 형식이 올바르지 않습니다."
        );
      }
    } catch (requestError) {
      console.error(
        "행동 로그 조회 실패:",
        requestError
      );

      setLogs([]);

      setError(
        requestError.message ??
          "행동 로그를 불러오지 못했습니다."
      );
    } finally {
      setLoading(false);
    }
  }


  /**
   * 페이지 최초 진입 시 로그 조회
   */
  useEffect(() => {
    loadLogs();
  }, []);


  /**
   * 검색 조건에 맞춰
   * 로그 필터링 및 최신순 정렬
   */
  const filteredLogs = useMemo(() => {
    return logs
      .filter((log) => {
        const logUserId = String(
          log.user_id ?? ""
        ).toLowerCase();

        const searchUserId =
          appliedFilters.userId
            .trim()
            .toLowerCase();

        const matchesUserId =
          searchUserId === "" ||
          logUserId.includes(searchUserId);

        const matchesRiskLevel =
          appliedFilters.riskLevel === "all" ||
          log.risk_level ===
            appliedFilters.riskLevel;

        const createdTime = log.created_at
          ? new Date(log.created_at).getTime()
          : null;

        const startTime =
          appliedFilters.startDate
            ? new Date(
                `${appliedFilters.startDate}T00:00:00`
              ).getTime()
            : null;

        const endTime =
          appliedFilters.endDate
            ? new Date(
                `${appliedFilters.endDate}T23:59:59`
              ).getTime()
            : null;

        const matchesStartDate =
          startTime === null ||
          (
            createdTime !== null &&
            createdTime >= startTime
          );

        const matchesEndDate =
          endTime === null ||
          (
            createdTime !== null &&
            createdTime <= endTime
          );

        return (
          matchesUserId &&
          matchesRiskLevel &&
          matchesStartDate &&
          matchesEndDate
        );
      })
      .sort((firstLog, secondLog) => {
        const firstTime = new Date(
          firstLog.created_at ?? 0
        ).getTime();

        const secondTime = new Date(
          secondLog.created_at ?? 0
        ).getTime();

        return secondTime - firstTime;
      });
  }, [logs, appliedFilters]);


  /**
   * 검색 입력값 변경
   */
  function handleFilterChange(event) {
    const { name, value } = event.target;

    setFilters((previousFilters) => ({
      ...previousFilters,
      [name]: value,
    }));
  }


  /**
   * 검색 적용
   */
  function handleSearch(event) {
    event.preventDefault();

    if (
      filters.startDate &&
      filters.endDate &&
      filters.startDate >
        filters.endDate
    ) {
      setError(
        "시작 날짜는 종료 날짜보다 늦을 수 없습니다."
      );

      return;
    }

    setError("");

    setAppliedFilters(filters);
  }


  /**
   * 검색 조건 초기화
   */
  function handleReset() {
    setFilters(INITIAL_FILTERS);

    setAppliedFilters(INITIAL_FILTERS);

    setSelectedLog(null);

    setError("");
  }


  /**
   * 테이블 행 클릭
   */
  function handleRowSelect(log) {
    setSelectedLog(log);
  }


  /**
   * 특정 행동 로그 삭제
   */
  async function handleDelete(log) {
    const confirmed = window.confirm(
      `${
        log.user_id ?? "선택한 사용자"
      }의 행동 로그를 삭제하시겠습니까?`
    );

    if (!confirmed) {
      return;
    }

    setDeletingId(log.id);

    setError("");

    try {
      await deleteEventLog(log.id);

      setLogs((previousLogs) =>
        previousLogs.filter(
          (previousLog) =>
            previousLog.id !== log.id
        )
      );

      // 현재 선택된 로그를 삭제한 경우
      if (selectedLog?.id === log.id) {
        setSelectedLog(null);
      }
    } catch (deleteError) {
      console.error(
        "행동 로그 삭제 실패:",
        deleteError
      );

      setError(
        deleteError.message ??
          "행동 로그를 삭제하지 못했습니다."
      );
    } finally {
      setDeletingId(null);
    }
  }


  return (
    <main className="page-container">
      <section className="page-card">

        {/* 페이지 상단 */}
        <div className="page-header">
          <div>
            <h1 className="page-title">
              행동 로그 조회
            </h1>

            <p className="page-description">
              수집된 사용자 행동 데이터와
              계산된 위험도를 확인합니다.
            </p>
          </div>

          <button
            type="button"
            className="action-button"
            onClick={loadLogs}
            disabled={loading}
          >
            {loading
              ? "불러오는 중..."
              : "새로고침"}
          </button>
        </div>


        {/* 검색 필터 */}
        <form
          className="event-filter-card"
          onSubmit={handleSearch}
        >
          <label
            className="
              filter-field
              event-user-filter
            "
          >
            <span>
              사용자 ID
            </span>

            <input
              type="text"
              name="userId"
              value={filters.userId}
              onChange={handleFilterChange}
              placeholder="예: user01"
            />
          </label>


          <label className="filter-field">
            <span>
              위험 등급
            </span>

            <select
              name="riskLevel"
              value={filters.riskLevel}
              onChange={handleFilterChange}
            >
              <option value="all">
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


          <label className="filter-field">
            <span>
              시작 날짜
            </span>

            <input
              type="date"
              name="startDate"
              value={filters.startDate}
              onChange={handleFilterChange}
            />
          </label>


          <label className="filter-field">
            <span>
              종료 날짜
            </span>

            <input
              type="date"
              name="endDate"
              value={filters.endDate}
              onChange={handleFilterChange}
            />
          </label>


          <div className="event-filter-actions">
            <button
              type="submit"
              className="action-button"
            >
              조회
            </button>

            <button
              type="button"
              className="secondary-button"
              onClick={handleReset}
            >
              초기화
            </button>
          </div>
        </form>


        {/* 조회 결과 */}
        <div
          className="
            result-summary
            event-result-summary
          "
        >
          <span>
            전체 로그{" "}
            <strong>
              {logs.length}
            </strong>
            건
          </span>

          <span>
            조회 결과{" "}
            <strong>
              {filteredLogs.length}
            </strong>
            건
          </span>
        </div>


        {/* 오류 */}
        {error && (
          <p className="error-message">
            {error}
          </p>
        )}


        {/* 행동 로그 테이블 */}
        <EventLogTable
          logs={filteredLogs}
          loading={loading}
          onRowSelect={handleRowSelect}
          onDelete={handleDelete}
          deletingId={deletingId}
        />


        {/* 선택한 로그 상세 */}
        {selectedLog && (
          <section className="event-detail-card">

            <div className="event-detail-header">
              <div>
                <h2>
                  탐지 상세
                </h2>

                <p>
                  선택한 행동 로그의
                  지속 인증 및 위험 탐지 결과입니다.
                </p>
              </div>

              <button
                type="button"
                className="secondary-button"
                onClick={() =>
                  setSelectedLog(null)
                }
              >
                닫기
              </button>
            </div>


            <div className="event-detail-grid">

              {/* 사용자 */}
              <div className="event-detail-item">
                <span>
                  사용자 ID
                </span>

                <strong>
                  {selectedLog.user_id ??
                    "-"}
                </strong>
              </div>


              {/* 장치 */}
              <div className="event-detail-item">
                <span>
                  장치
                </span>

                <strong>
                  {selectedLog.device_id ??
                    "-"}
                </strong>
              </div>


              {/* 위치 */}
              <div className="event-detail-item">
                <span>
                  위치
                </span>

                <strong>
                  {selectedLog.location ??
                    "-"}
                </strong>
              </div>


              {/* 발생 시간 */}
              <div className="event-detail-item">
                <span>
                  발생 시간
                </span>

                <strong>
                  {selectedLog.created_at
                    ? new Date(
                        selectedLog.created_at
                      ).toLocaleString()
                    : "-"}
                </strong>
              </div>


              {/* 타이핑 속도 */}
              <div className="event-detail-item">
                <span>
                  타이핑 속도
                </span>

                <strong>
                  {selectedLog.typing_speed ??
                    "-"}
                </strong>
              </div>


              {/* Hold Time */}
              <div className="event-detail-item">
                <span>
                  평균 Hold Time
                </span>

                <strong>
                  {selectedLog.avg_hold_time ??
                    "-"}
                </strong>
              </div>


              {/* Flight Time */}
              <div className="event-detail-item">
                <span>
                  평균 Flight Time
                </span>

                <strong>
                  {selectedLog.avg_flight_time ??
                    "-"}
                </strong>
              </div>


              {/* 키 입력 수 */}
              <div className="event-detail-item">
                <span>
                  키 입력 수
                </span>

                <strong>
                  {selectedLog.total_keystrokes ??
                    "-"}
                </strong>
              </div>


              {/* 마우스 이동 */}
              <div className="event-detail-item">
                <span>
                  마우스 이동
                </span>

                <strong>
                  {selectedLog.mouse_move_count ??
                    "-"}
                </strong>
              </div>


              {/* 클릭 */}
              <div className="event-detail-item">
                <span>
                  클릭 수
                </span>

                <strong>
                  {selectedLog.click_count ??
                    "-"}
                </strong>
              </div>


              {/* ML 이상 탐지 */}
              <div className="event-detail-item">
                <span>
                  ML 이상 탐지
                </span>

                <strong>
                  {selectedLog.detect_anomaly
                    ? "이상"
                    : "정상"}
                </strong>
              </div>


              {/* 프로필 편차 */}
              <div className="event-detail-item">
                <span>
                  프로필 편차 점수
                </span>

                <strong>
                  {
                    selectedLog
                      .profile_deviation_score ??
                    "-"
                  }
                </strong>
              </div>


              {/* Risk Score */}
              <div className="event-detail-item">
                <span>
                  Risk Score
                </span>

                <strong>
                  {selectedLog.risk_score ??
                    "-"}
                </strong>
              </div>


              {/* Risk Level */}
              <div className="event-detail-item">
                <span>
                  Risk Level
                </span>

                <strong>
                  {selectedLog.risk_level ??
                    "-"}
                </strong>
              </div>

            </div>
          </section>
        )}

      </section>
    </main>
  );
}