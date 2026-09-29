function ScoreRow({ label, value }) {
  return (
    <li>
      <strong>{label}:</strong>{" "}
      {typeof value === "number" ? value.toFixed(1) : "-"}
    </li>
  );
}

function RiskScoreBreakdown({ assessment }) {
  if (!assessment) return null;

  return (
    <section aria-labelledby="risk-score-heading">
      <h3 id="risk-score-heading">위험 점수</h3>

      <ul>
        <ScoreRow label="행동 위험 점수" value={assessment.behavior_score} />
        <ScoreRow label="신원 위험 점수" value={assessment.identity_score} />
        <ScoreRow label="거래 위험 점수" value={assessment.transaction_score} />
        <ScoreRow label="최종 위험 점수" value={assessment.final_risk_score} />
      </ul>

      <p>
        <strong>위험 등급:</strong> {assessment.risk_level ?? "-"}
      </p>
      <p>
        <strong>결정:</strong> {assessment.decision ?? "-"}
      </p>
    </section>
  );
}

export default RiskScoreBreakdown;