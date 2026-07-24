const WIDTH = 760;
const HEIGHT = 300;
const MARGIN = { top: 22, right: 24, bottom: 48, left: 52 };
const Y_TICKS = [0, 25, 50, 75, 100];

function clampScore(value) {
  const score = Number(value);
  return Number.isFinite(score) ? Math.min(100, Math.max(0, score)) : null;
}

function toDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatTime(value, includeDate = false) {
  const date = toDate(value);

  if (!date) {
    return "시간 정보 없음";
  }

  return new Intl.DateTimeFormat("ko-KR", {
    ...(includeDate && { month: "numeric", day: "numeric" }),
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

function normalizeData(data) {
  if (!Array.isArray(data)) {
    return [];
  }

  return data
    .map((item, index) => {
      const timestamp = item?.timestamp ?? item?.created_at ?? item?.createdAt;
      const riskScore = clampScore(
        item?.riskScore ?? item?.risk_score ?? item?.score,
      );
      const date = toDate(timestamp);

      if (riskScore === null || !date) {
        return null;
      }

      return {
        id: item?.id ?? `${date.getTime()}-${index}`,
        timestamp,
        date,
        riskScore,
      };
    })
    .filter(Boolean)
    .sort((a, b) => a.date - b.date);
}

function RiskLineChart({ data = [], loading = false }) {
  const points = normalizeData(data);

  if (loading) {
    return (
      <section className="risk-chart-panel" aria-labelledby="risk-chart-title">
        <div className="risk-chart-heading">
          <div>
            <span className="section-eyebrow">RISK TREND</span>
            <h2 id="risk-chart-title">최근 리스크 점수 변화</h2>
          </div>
        </div>
        <div className="risk-chart-loading" role="status">
          그래프 데이터를 불러오는 중입니다…
        </div>
      </section>
    );
  }

  if (points.length === 0) {
    return (
      <section className="risk-chart-panel" aria-labelledby="risk-chart-title">
        <div className="risk-chart-heading">
          <div>
            <span className="section-eyebrow">RISK TREND</span>
            <h2 id="risk-chart-title">최근 리스크 점수 변화</h2>
          </div>
        </div>
        <div className="risk-chart-empty" role="status">
          <span aria-hidden="true">⌁</span>
          <strong>표시할 리스크 기록이 없습니다.</strong>
          <p>사용자 행동 분석이 완료되면 시간별 변화가 표시됩니다.</p>
        </div>
      </section>
    );
  }

  const plotWidth = WIDTH - MARGIN.left - MARGIN.right;
  const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom;
  const xFor = (index) =>
    MARGIN.left +
    (points.length === 1 ? plotWidth / 2 : (index / (points.length - 1)) * plotWidth);
  const yFor = (score) => MARGIN.top + plotHeight - (score / 100) * plotHeight;
  const linePoints = points
    .map((point, index) => `${xFor(index)},${yFor(point.riskScore)}`)
    .join(" ");
  const maxLabels = 6;
  const labelStep = Math.max(1, Math.ceil(points.length / maxLabels));
  const xLabelIndexes = points
    .map((_, index) => index)
    .filter(
      (index) =>
        index === 0 || index === points.length - 1 || index % labelStep === 0,
    );
  const latest = points[points.length - 1];
  const average =
    points.reduce((sum, point) => sum + point.riskScore, 0) / points.length;

  return (
    <section className="risk-chart-panel" aria-labelledby="risk-chart-title">
      <div className="risk-chart-heading">
        <div>
          <span className="section-eyebrow">RISK TREND</span>
          <h2 id="risk-chart-title">최근 리스크 점수 변화</h2>
        </div>
        <div className="risk-chart-summary" aria-label="그래프 요약">
          <span>
            현재 <strong>{latest.riskScore.toFixed(1)}</strong>
          </span>
          <span>
            평균 <strong>{average.toFixed(1)}</strong>
          </span>
        </div>
      </div>

      <div className="risk-chart-scroll">
        <svg
          className="risk-line-chart"
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          role="img"
          aria-labelledby="risk-chart-svg-title risk-chart-svg-desc"
        >
          <title id="risk-chart-svg-title">시간별 리스크 점수 선 그래프</title>
          <desc id="risk-chart-svg-desc">
            0점부터 100점 사이의 리스크 점수 {points.length}개를 시간순으로
            표시합니다.
          </desc>

          <defs>
            <linearGradient id="riskAreaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6d5dfc" stopOpacity="0.24" />
              <stop offset="100%" stopColor="#6d5dfc" stopOpacity="0" />
            </linearGradient>
          </defs>

          {Y_TICKS.map((tick) => {
            const y = yFor(tick);
            return (
              <g key={tick}>
                <line
                  x1={MARGIN.left}
                  y1={y}
                  x2={WIDTH - MARGIN.right}
                  y2={y}
                  className="risk-chart-grid"
                />
                <text x={MARGIN.left - 13} y={y + 4} className="risk-chart-axis-y">
                  {tick}
                </text>
              </g>
            );
          })}

          {points.length > 1 && (
            <polygon
              points={`${MARGIN.left},${MARGIN.top + plotHeight} ${linePoints} ${
                WIDTH - MARGIN.right
              },${MARGIN.top + plotHeight}`}
              fill="url(#riskAreaGradient)"
            />
          )}

          <polyline points={linePoints} className="risk-chart-line" />

          {points.map((point, index) => (
            <circle
              key={point.id}
              cx={xFor(index)}
              cy={yFor(point.riskScore)}
              r="4"
              className="risk-chart-point"
              tabIndex="0"
              aria-label={`${formatTime(point.timestamp, true)}, ${point.riskScore}점`}
            >
              <title>
                {formatTime(point.timestamp, true)} · {point.riskScore}점
              </title>
            </circle>
          ))}

          {xLabelIndexes.map((index) => (
            <text
              key={points[index].id}
              x={xFor(index)}
              y={HEIGHT - 17}
              className="risk-chart-axis-x"
            >
              {formatTime(points[index].timestamp)}
            </text>
          ))}
        </svg>
      </div>
    </section>
  );
}

export default RiskLineChart;