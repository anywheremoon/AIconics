import { useEffect, useMemo, useState } from "react";

import RiskCard from "../components/RiskCard";
import RiskLineChart from "../components/RiskLineChart";
import { getEventLogs } from "../api/riskApi.js";


const DASHBOARD_STYLES = `
  .dashboard-page {
    min-height: 100vh;
    padding: clamp(24px, 4vw, 56px);
    color: #202338;
    background:
      radial-gradient(
        circle at 8% 0%,
        rgba(109, 93, 252, .10),
        transparent 28rem
      ),
      #f6f7fb;
    font-family:
      Inter,
      Pretendard,
      "Noto Sans KR",
      system-ui,
      sans-serif;
  }

  .dashboard-content {
    width: min(1180px, 100%);
    margin: 0 auto;
  }

  .dashboard-header {
    margin-bottom: 30px;
  }

  .dashboard-eyebrow,
  .section-eyebrow {
    display: block;
    margin-bottom: 8px;
    color: #6d5dfc;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: .14em;
  }

  .dashboard-header h1 {
    margin: 0;
    font-size: clamp(28px, 4vw, 42px);
    letter-spacing: -.04em;
  }

  .dashboard-header p {
    margin: 10px 0 0;
    color: #70748a;
    font-size: 15px;
  }

  .risk-card-container {
    display: grid;
    grid-template-columns:
      repeat(3, minmax(0, 1fr));
    gap: 16px;
    margin-bottom: 22px;
  }

  .risk-card {
    position: relative;
    min-width: 0;
    padding: 22px;
    overflow: hidden;
    border: 1px solid #e8e9f1;
    border-radius: 18px;
    background: rgba(255, 255, 255, .94);
    box-shadow:
      0 12px 34px
      rgba(40, 44, 74, .06);
  }

  .risk-card::after {
    content: "";
    position: absolute;
    right: -26px;
    bottom: -36px;
    width: 100px;
    height: 100px;
    border-radius: 50%;
    background: var(--risk-color);
    opacity: .07;
  }

  .risk-card-neutral {
    --risk-color: #6d5dfc;
  }

  .risk-card-low {
    --risk-color: #20a778;
  }

  .risk-card-medium {
    --risk-color: #e39b25;
  }

  .risk-card-high {
    --risk-color: #e95768;
  }

  .risk-card-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }

  .risk-card-heading h2 {
    margin: 0;
    color: #74788e;
    font-size: 14px;
    font-weight: 700;
  }

  .risk-card-indicator {
    width: 9px;
    height: 9px;
    flex: 0 0 auto;
    border-radius: 50%;
    background: var(--risk-color);
  }

  .risk-card-value {
    display: block;
    margin: 18px 0 8px;
    color: #202338;
    font-size: clamp(25px, 2.7vw, 34px);
    line-height: 1;
    letter-spacing: -.04em;
  }

  .risk-card p {
    min-height: 36px;
    margin: 0;
    color: #9093a4;
    font-size: 12px;
    line-height: 1.5;
  }

  .risk-chart-panel {
    padding: clamp(20px, 3vw, 30px);
    border: 1px solid #e8e9f1;
    border-radius: 22px;
    background: #fff;
    box-shadow:
      0 16px 40px
      rgba(40, 44, 74, .06);
  }

  .risk-chart-heading {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 24px;
    margin-bottom: 22px;
  }

  .risk-chart-heading h2 {
    margin: 0;
    font-size: 20px;
    letter-spacing: -.025em;
  }

  .risk-chart-summary {
    display: flex;
    gap: 18px;
    color: #85889a;
    font-size: 13px;
    white-space: nowrap;
  }

  .risk-chart-summary strong {
    margin-left: 4px;
    color: #34374d;
    font-size: 17px;
  }

  .risk-chart-scroll {
    width: 100%;
    overflow-x: auto;
  }

  .risk-line-chart {
    display: block;
    width: 100%;
    min-width: 580px;
    height: auto;
    overflow: visible;
  }

  .risk-chart-grid {
    stroke: #ececf3;
    stroke-width: 1;
    stroke-dasharray: 4 5;
  }

  .risk-chart-line {
    fill: none;
    stroke: #6d5dfc;
    stroke-width: 3;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .risk-chart-point {
    fill: #fff;
    stroke: #6d5dfc;
    stroke-width: 3;
    cursor: help;
  }

  .risk-chart-axis-x,
  .risk-chart-axis-y {
    fill: #9295a7;
    font-size: 11px;
  }

  .dashboard-loading,
  .dashboard-error,
  .dashboard-empty {
    padding: 18px 20px;
    margin-bottom: 20px;
    border-radius: 14px;
    font-size: 14px;
  }

  .dashboard-loading {
    color: #5752a8;
    background: #eceaff;
  }

  .dashboard-error {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    color: #a62c3d;
    background: #fff0f2;
  }

  .dashboard-error button {
    padding: 8px 13px;
    border: 0;
    border-radius: 9px;
    color: #fff;
    background: #c83d50;
    font: inherit;
    font-weight: 700;
    cursor: pointer;
  }

  .dashboard-empty {
    color: #686b7d;
    background: #fff;
    border: 1px solid #e8e9f1;
  }

  .risk-card-skeleton .risk-card-value,
  .risk-card-skeleton p {
    color: transparent;
    border-radius: 8px;
    background:
      linear-gradient(
        90deg,
        #eeeef4 25%,
        #f8f8fb 50%,
        #eeeef4 75%
      );
    background-size: 200% 100%;
    animation:
      dashboard-shimmer 1.4s infinite;
  }

  @keyframes dashboard-shimmer {
    to {
      background-position: -200% 0;
    }
  }

  @media (max-width: 980px) {
    .risk-card-container {
      grid-template-columns:
        repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 600px) {
    .dashboard-page {
      padding: 22px 16px 32px;
    }

    .risk-card-container {
      grid-template-columns: 1fr;
      gap: 12px;
    }

    .risk-card {
      padding: 19px;
    }

    .risk-card p {
      min-height: auto;
    }

    .dashboard-error {
      align-items: flex-start;
      flex-direction: column;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .risk-card-skeleton .risk-card-value,
    .risk-card-skeleton p {
      animation: none;
    }
  }
`;


/**
 * 위험 등급 정규화
 */
function normalizeLevel(level, score) {
  const normalized =
    String(level ?? "").toLowerCase();

  if (
    ["low", "normal", "safe"].includes(
      normalized
    )
  ) {
    return "low";
  }

  if (
    [
      "medium",
      "warning",
      "caution",
    ].includes(normalized)
  ) {
    return "medium";
  }

  if (
    [
      "high",
      "danger",
      "critical",
    ].includes(normalized)
  ) {
    return "high";
  }

  if (score >= 70) {
    return "high";
  }

  if (score >= 40) {
    return "medium";
  }

  return "low";
}


/**
 * 백엔드 Event 형식을
 * Dashboard에서 사용하기 좋은 형태로 변환
 */
function normalizeEvents(payload) {
  const source = Array.isArray(payload)
    ? payload
    : payload?.events ??
      payload?.data ??
      payload?.items ??
      [];

  if (!Array.isArray(source)) {
    return [];
  }

  return source
    .map((event, index) => {
      const score = Number(
        event?.risk_score ??
          event?.riskScore ??
          event?.score
      );

      const userId =
        event?.user_id ??
        event?.userId;

      const timestamp =
        event?.created_at ??
        event?.createdAt ??
        event?.timestamp ??
        event?.date;

      if (
        !userId ||
        !Number.isFinite(score)
      ) {
        return null;
      }

      return {
        id:
          event?.id ??
          `${userId}-${timestamp ?? index}`,

        userId:
          String(userId),

        riskScore:
          Math.min(
            100,
            Math.max(0, score)
          ),

        riskLevel:
          normalizeLevel(
            event?.risk_level ??
              event?.riskLevel,
            score
          ),

        timestamp,

        // 6단계 ML 이상 탐지 결과
        detectAnomaly:
          Boolean(
            event?.detect_anomaly ??
              event?.is_anomaly ??
              event?.detectAnomaly ??
              false
          ),

        // 프로필 차이 점수
        profileDeviationScore:
          event?.profile_deviation_score ??
          event?.profileDeviationScore ??
          null,
      };
    })
    .filter(Boolean);
}


/**
 * 오늘 발생한 이벤트인지 확인
 */
function isToday(timestamp) {
  if (!timestamp) {
    return false;
  }

  const date = new Date(timestamp);

  if (Number.isNaN(date.getTime())) {
    return false;
  }

  const today = new Date();

  return (
    date.getFullYear() ===
      today.getFullYear() &&
    date.getMonth() ===
      today.getMonth() &&
    date.getDate() ===
      today.getDate()
  );
}


/**
 * Dashboard 통계 계산
 */
function calculateSummary(events) {
  const latestByUser = new Map();

  events.forEach((event) => {
    const current =
      latestByUser.get(event.userId);

    const eventTime =
      new Date(
        event.timestamp ?? 0
      ).getTime();

    const currentTime =
      new Date(
        current?.timestamp ?? 0
      ).getTime();

    if (
      !current ||
      eventTime >= currentTime
    ) {
      latestByUser.set(
        event.userId,
        event
      );
    }
  });


  // 사용자별 가장 최근 이벤트
  const users = [
    ...latestByUser.values(),
  ];


  // 위험 등급별 사용자 수
  const counts = users.reduce(
    (result, user) => {
      result[user.riskLevel] += 1;

      return result;
    },
    {
      low: 0,
      medium: 0,
      high: 0,
    }
  );


  // 오늘 이벤트 수
  const todayEventCount =
    events.filter((event) =>
      isToday(event.timestamp)
    ).length;


  // ML 이상 탐지 이벤트 수
  const anomalyCount =
    events.filter(
      (event) =>
        event.detectAnomaly
    ).length;


  return {
    total: users.length,

    ...counts,

    todayEventCount,

    anomalyCount,
  };
}


function DashboardPage() {
  const [events, setEvents] =
    useState([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState(null);

  const [reloadKey, setReloadKey] =
    useState(0);


  /**
   * 행동 로그 조회
   */
  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      setLoading(true);
      setError(null);

      try {
        const payload =
          await getEventLogs();

        if (!cancelled) {
          setEvents(
            normalizeEvents(payload)
          );
        }

      } catch (requestError) {

        if (!cancelled) {
          setEvents([]);

          setError(
            requestError?.message ||
              "위험도 데이터를 불러오지 못했습니다."
          );
        }

      } finally {

        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadDashboard();

    return () => {
      cancelled = true;
    };

  }, [reloadKey]);


  /**
   * Dashboard 요약
   */
  const summary = useMemo(
    () => calculateSummary(events),
    [events]
  );


  /**
   * 위험도 변화 그래프
   */
  const riskHistory = useMemo(
    () =>
      events
        .filter(
          (event) =>
            event.timestamp
        )
        .map((event) => ({
          id: event.id,
          timestamp:
            event.timestamp,
          riskScore:
            event.riskScore,
        })),
    [events]
  );


  /**
   * 6단계 Dashboard 카드
   */
  const cards = [
    {
      title: "전체 사용자",

      value:
        `${summary.total.toLocaleString()}명`,

      level: "neutral",

      description:
        "지속 인증 분석 대상 전체 사용자",
    },

    {
      title: "오늘 이벤트",

      value:
        `${summary.todayEventCount.toLocaleString()}건`,

      level: "neutral",

      description:
        "오늘 Agent에서 수집된 행동 이벤트",
    },

    {
      title: "정상 사용자",

      value:
        `${summary.low.toLocaleString()}명`,

      level: "low",

      description:
        "Risk Score 40점 미만",
    },

    {
      title: "주의 사용자",

      value:
        `${summary.medium.toLocaleString()}명`,

      level: "medium",

      description:
        "Risk Score 40점 이상 70점 미만",
    },

    {
      title: "위험 사용자",

      value:
        `${summary.high.toLocaleString()}명`,

      level: "high",

      description:
        "Risk Score 70점 이상",
    },

    {
      title: "ML 이상 탐지",

      value:
        `${summary.anomalyCount.toLocaleString()}건`,

      level:
        summary.anomalyCount > 0
          ? "high"
          : "low",

      description:
        "One-Class SVM이 이상으로 판단한 이벤트",
    },
  ];


  return (
    <main className="dashboard-page">

      <style>
        {DASHBOARD_STYLES}
      </style>


      <div className="dashboard-content">

        {/* Dashboard Header */}
        <header className="dashboard-header">

          <span className="dashboard-eyebrow">
            SECURITY OVERVIEW
          </span>

          <h1>
            보안 위험도 대시보드
          </h1>

          <p>
            지속 인증 행동 분석과
            합성 신원 탐지 결과를
            한눈에 확인하세요.
          </p>

        </header>


        {/* Loading */}
        {loading && (
          <div
            className="dashboard-loading"
            role="status"
            aria-live="polite"
          >
            위험도 데이터를 불러오는
            중입니다…
          </div>
        )}


        {/* Error */}
        {error && (
          <div
            className="dashboard-error"
            role="alert"
          >

            <span>
              {error}
            </span>

            <button
              type="button"
              onClick={() =>
                setReloadKey(
                  (key) => key + 1
                )
              }
            >
              다시 시도
            </button>

          </div>
        )}


        {/* Empty */}
        {!loading &&
          !error &&
          events.length === 0 && (

            <div
              className="dashboard-empty"
              role="status"
            >
              아직 분석된 사용자 데이터가
              없습니다. Agent에서 이벤트가
              수집되면 자동으로 표시됩니다.
            </div>

          )}


        {/* Risk Summary Cards */}
        <section
          className="risk-card-container"
          aria-label="위험도 요약"
        >

          {loading
            ? cards.map((card) => (

                <div
                  className="risk-card-skeleton"
                  key={card.title}
                >
                  <RiskCard
                    title={card.title}
                    value="불러오는 중"
                    level="neutral"
                    description=
                      "데이터를 확인하고 있습니다."
                  />
                </div>

              ))

            : cards.map((card) => (

                <RiskCard
                  key={card.title}
                  {...card}
                />

              ))}

        </section>


        {/* 위험도 변화 그래프 */}
        <RiskLineChart
          data={riskHistory}
          loading={loading}
        />

      </div>

    </main>
  );
}


export default DashboardPage;