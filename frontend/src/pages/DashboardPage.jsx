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
      radial-gradient(circle at 8% 0%, rgba(109, 93, 252, .10), transparent 28rem),
      #f6f7fb;
    font-family: Inter, Pretendard, "Noto Sans KR", system-ui, sans-serif;
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
    grid-template-columns: repeat(5, minmax(0, 1fr));
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
    box-shadow: 0 12px 34px rgba(40, 44, 74, .06);
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
    box-shadow:
      0 0 0 5px
      color-mix(
        in srgb,
        var(--risk-color) 12%,
        transparent
      );
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
    box-shadow: 0 16px 40px rgba(40, 44, 74, .06);
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

  .risk-chart-point:focus {
    outline: none;
    fill: #6d5dfc;
    stroke: #fff;
  }

  .risk-chart-axis-x,
  .risk-chart-axis-y {
    fill: #9295a7;
    font-size: 11px;
  }

  .risk-chart-axis-x {
    text-anchor: middle;
  }

  .risk-chart-axis-y {
    text-anchor: end;
  }

  .risk-chart-empty {
    display: grid;
    min-height: 260px;
    place-items: center;
    align-content: center;
    padding: 20px;
    border: 1px dashed #dedfeb;
    border-radius: 16px;
    color: #777b91;
    text-align: center;
  }

  .risk-chart-loading {
    display: grid;
    min-height: 260px;
    place-items: center;
    border-radius: 16px;
    color: #73768a;
    background:
      linear-gradient(
        100deg,
        #f4f4f8 20%,
        #fafafe 45%,
        #f4f4f8 70%
      );
    background-size: 200% 100%;
    animation: dashboard-shimmer 1.4s infinite;
  }

  .risk-chart-empty span {
    margin-bottom: 10px;
    color: #a3a0ff;
    font-size: 38px;
  }

  .risk-chart-empty strong {
    color: #3f4257;
    font-size: 15px;
  }

  .risk-chart-empty p {
    margin: 7px 0 0;
    font-size: 13px;
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
    animation: dashboard-shimmer 1.4s infinite;
  }

  @keyframes dashboard-shimmer {
    to {
      background-position: -200% 0;
    }
  }

  @media (max-width: 980px) {
    .risk-card-container {
      grid-template-columns: repeat(2, minmax(0, 1fr));
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

    .risk-chart-heading {
      display: block;
    }

    .risk-chart-summary {
      margin-top: 15px;
    }

    .dashboard-error {
      align-items: flex-start;
      flex-direction: column;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .risk-card-skeleton .risk-card-value,
    .risk-card-skeleton p,
    .risk-chart-loading {
      animation: none;
    }
  }
`;

function normalizeLevel(level, score) {
  const normalized = String(level ?? "").toLowerCase();

  if (
    ["low", "normal", "safe"].includes(normalized)
  ) {
    return "low";
  }

  if (
    ["medium", "warning", "caution"].includes(normalized)
  ) {
    return "medium";
  }

  if (
    ["high", "danger", "critical"].includes(normalized)
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

        userId: String(userId),

        riskScore: Math.min(
          100,
          Math.max(0, score)
        ),

        riskLevel: normalizeLevel(
          event?.risk_level ??
            event?.riskLevel,
          score
        ),

        timestamp,
      };
    })
    .filter(Boolean);
}

function calculateSummary(events) {
  const latestByUser = new Map();

  events.forEach((event) => {
    const current =
      latestByUser.get(event.userId);

    const parsedEventTime =
      new Date(
        event.timestamp ?? 0
      ).getTime();

    const parsedCurrentTime =
      new Date(
        current?.timestamp ?? 0
      ).getTime();

    const eventTime =
      Number.isFinite(parsedEventTime)
        ? parsedEventTime
        : 0;

    const currentTime =
      Number.isFinite(parsedCurrentTime)
        ? parsedCurrentTime
        : 0;

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

  const users = [
    ...latestByUser.values(),
  ];

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

  const averageRiskScore =
    users.length > 0
      ? users.reduce(
          (sum, user) =>
            sum + user.riskScore,
          0
        ) / users.length
      : 0;

  return {
    total: users.length,
    ...counts,
    averageRiskScore,
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

  const summary = useMemo(
    () => calculateSummary(events),
    [events]
  );

  const riskHistory = useMemo(
    () =>
      events
        .filter(
          (event) => event.timestamp
        )
        .map((event) => ({
          id: event.id,
          timestamp: event.timestamp,
          riskScore: event.riskScore,
        })),
    [events]
  );

  const cards = [
    {
      title: "전체 사용자",
      value: `${summary.total.toLocaleString()}명`,
      level: "neutral",
      description:
        "현재 위험도를 분석한 전체 사용자",
    },
    {
      title: "정상 사용자",
      value: `${summary.low.toLocaleString()}명`,
      level: "low",
      description:
        "리스크 점수 40점 미만",
    },
    {
      title: "주의 사용자",
      value: `${summary.medium.toLocaleString()}명`,
      level: "medium",
      description:
        "리스크 점수 40점 이상 70점 미만",
    },
    {
      title: "위험 사용자",
      value: `${summary.high.toLocaleString()}명`,
      level: "high",
      description:
        "즉시 확인이 필요한 사용자",
    },
    {
      title: "평균 리스크",
      value:
        `${summary.averageRiskScore.toFixed(1)}점`,
      level:
        summary.averageRiskScore >= 70
          ? "high"
          : summary.averageRiskScore >= 40
            ? "medium"
            : "low",
      description:
        "사용자별 최신 점수의 평균",
    },
  ];

  return (
    <main className="dashboard-page">
      <style>
        {DASHBOARD_STYLES}
      </style>

      <div className="dashboard-content">
        <header className="dashboard-header">
          <span className="dashboard-eyebrow">
            SECURITY OVERVIEW
          </span>

          <h1>
            보안 위험도 대시보드
          </h1>

          <p>
            사용자 행동 분석 결과와 최근
            리스크 변화를 한눈에 확인하세요.
          </p>
        </header>

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

        {!loading &&
          !error &&
          events.length === 0 && (
            <div
              className="dashboard-empty"
              role="status"
            >
              아직 분석된 사용자 데이터가
              없습니다. 이벤트가 수집되면
              현황이 자동으로 표시됩니다.
            </div>
          )}

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
                    description="데이터를 확인하고 있습니다."
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

        <RiskLineChart
          data={riskHistory}
          loading={loading}
        />
      </div>
    </main>
  );
}

export default DashboardPage;