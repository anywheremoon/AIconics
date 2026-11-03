export default function EthVaultTimeline({ transfer, now }) {
  const authRequired = transfer.riskLevel === "MEDIUM";
  const approvalRequired = transfer.riskLevel === "HIGH";
  const terminal = transfer.status !== "PENDING";
  const expired = now >= transfer.expiresAt;

  const remaining = Math.max(
    0,
    Math.ceil((transfer.unlockAt - now) / 1000)
  );

  let finalText = "송금 실행 대기";

  if (transfer.status === "EXECUTED") finalText = "송금 완료";
  else if (transfer.status === "REFUNDED") finalText = "거절 및 환불 완료";
  else if (transfer.status === "CANCELLED") finalText = "만료 취소 및 환불 완료";
  else if (expired) finalText = "만료됨 · 취소 및 환불 필요";
  else if (transfer.riskLevel === "CRITICAL") finalText = "실행 차단 · 관리자 검토 필요";

  return (
    <ol className="ev-timeline">
      <li>✓ 송금 요청 생성 · Mock 예치</li>
      <li>✓ 위험 분석 완료: {transfer.riskLevel}</li>

      <li>
        {authRequired
          ? transfer.authCompleted
            ? "✓ 추가 인증 완료"
            : "○ 추가 인증 필요"
          : "— 추가 인증 대상 아님"}
      </li>

      <li>
        {approvalRequired
          ? transfer.adminApproved
            ? "✓ 관리자 승인 완료"
            : "○ 관리자 승인 대기"
          : "— 관리자 승인 단계 해당 없음"}
      </li>

      <li>
        {terminal || expired
          ? "— 타임락 단계 종료"
          : remaining > 0
            ? `○ 타임락 ${remaining}초 남음`
            : "✓ 타임락 대기 없음"}
      </li>

      <li>{finalText}</li>
    </ol>
  );
}