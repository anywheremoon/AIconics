import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { getRiskAssessment } from "../api/riskAssessmentApi.js";
import RiskFactorList from "../components/RiskFactorList.jsx";
import RiskScoreBreakdown from "../components/RiskScoreBreakdown.jsx";
import TransactionStatusBadge from "../components/TransactionStatusBadge.jsx";

const STATUS_MESSAGES = {
  COMPLETED: "거래가 완료되었습니다.",
  PENDING_VERIFICATION: "추가 인증이 필요합니다. 거래는 아직 처리되지 않았습니다.",
  PENDING_REVIEW: "거래가 검토 대기 중입니다. 거래는 아직 처리되지 않았습니다.",
  ACCOUNT_REVIEW: "계좌 검토가 필요합니다. 거래는 아직 처리되지 않았습니다.",
};

function TransactionResultPage() {
  const location = useLocation();
  const navigate = useNavigate();

  const data = location.state;
  const transaction = data?.result;
  const transactionId = transaction?.id;

  const [assessment, setAssessment] = useState(null);
  const [assessmentLoading, setAssessmentLoading] = useState(false);
  const [assessmentError, setAssessmentError] = useState(null);

  useEffect(() => {
    if (transactionId == null) return;

    let active = true;

    setAssessment(null);
    setAssessmentLoading(true);
    setAssessmentError(null);

    getRiskAssessment(transactionId)
      .then((result) => {
        if (active) {
          setAssessment(result);
        }
      })
      .catch((error) => {
        if (active) {
          setAssessmentError({
            status: error.status,
            message:
              error.message || "위험 평가 정보를 불러오지 못했습니다.",
          });
        }
      })
      .finally(() => {
        if (active) {
          setAssessmentLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [transactionId]);

  if (!data) {
    return (
      <main className="page-container transaction-page">
        <h1 className="page-title">거래 결과</h1>
        <p>표시할 거래 정보가 없습니다.</p>

        <button type="button" onClick={() => navigate("/account")}>
          계좌 화면으로 이동
        </button>
      </main>
    );
  }

  const status = transaction?.status;

  const transactionType =
    data.type === "TRANSFER"
      ? "계좌 이체"
      : data.type === "WITHDRAW"
        ? "출금"
        : data.type ?? "-";

  const message = !data.success
    ? "거래 요청에 실패했습니다."
    : STATUS_MESSAGES[status] ?? "거래 요청 결과를 확인하세요.";

  const createdAt = data.createdAt ?? transaction?.created_at;

  return (
    <main className="page-container transaction-page">
      <h1 className="page-title">거래 결과</h1>
      <h2>{message}</h2>

      {status && <TransactionStatusBadge status={status} />}

      <div>
        <p>
          <strong>거래 유형:</strong> {transactionType}
        </p>

        <p>
          <strong>거래 금액:</strong>{" "}
          {Number(data.amount).toLocaleString("ko-KR")}원
        </p>

        <p>
          <strong>Request ID:</strong>{" "}
          {data.requestId ?? transaction?.request_id ?? "-"}
        </p>

        <p>
          <strong>처리 시각:</strong>{" "}
          {createdAt
            ? new Date(createdAt).toLocaleString("ko-KR")
            : "-"}
        </p>

        {data.balanceAfter !== undefined && (
          <p>
            <strong>출금 후 잔액:</strong>{" "}
            {Number(data.balanceAfter).toLocaleString("ko-KR")}원
          </p>
        )}

        {!data.success && (
          <p>
            <strong>실패 사유:</strong>{" "}
            {data.error || "알 수 없는 오류"}
          </p>
        )}
      </div>

      {assessmentLoading && (
        <p>위험 평가 정보를 불러오는 중...</p>
      )}

      {assessmentError?.status === 404 && (
        <p>이 거래에는 위험 평가 기록이 없습니다.</p>
      )}

      {assessmentError && assessmentError.status !== 404 && (
        <p role="alert">{assessmentError.message}</p>
      )}

      {assessment && (
        <>
          <RiskScoreBreakdown assessment={assessment} />
          <RiskFactorList factors={assessment.factors ?? []} />
        </>
      )}

      <button type="button" onClick={() => navigate("/account")}>
        계좌 화면으로 이동
      </button>
    </main>
  );
}

export default TransactionResultPage;