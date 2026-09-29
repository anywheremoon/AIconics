function RiskFactorList({ factors = [] }) {
  return (
    <section aria-labelledby="risk-factor-heading">
      <h3 id="risk-factor-heading">판단 근거</h3>

      {factors.length === 0 ? (
        <p>표시할 판단 근거가 없습니다.</p>
      ) : (
        <ul>
          {factors.map((factor) => (
            <li key={factor.id}>
              <strong>{factor.description}</strong>

              {factor.reason_code && (
                <span> ({factor.reason_code})</span>
              )}

              {typeof factor.final_score_contribution === "number" && (
                <span>
                  {" "}
                  · 최종 점수 기여:{" "}
                  {factor.final_score_contribution.toFixed(1)}점
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default RiskFactorList;