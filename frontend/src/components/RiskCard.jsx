const VALID_LEVELS = new Set(["neutral", "low", "medium", "high"]);

function RiskCard({
  title = "위험도 정보",
  value,
  level = "neutral",
  description = "",
}) {
  const safeLevel = VALID_LEVELS.has(level) ? level : "neutral";
  const displayValue =
    value === null || value === undefined || value === "" ? "—" : value;

  return (
    <article
      className={`risk-card risk-card-${safeLevel}`}
      aria-label={`${title}: ${displayValue}`}
    >
      <div className="risk-card-heading">
        <h2>{title}</h2>
        <span className="risk-card-indicator" aria-hidden="true" />
      </div>
      <strong className="risk-card-value">{displayValue}</strong>
      {description && <p>{description}</p>}
    </article>
  );
}

export default RiskCard;
