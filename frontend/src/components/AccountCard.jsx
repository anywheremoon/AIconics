//계좌 정보를 카드 형태로 표시
function formatMoney(value) {
  if (value === undefined || value === null) {
    return "0원";
  }

  const number = Number(value);

  if (Number.isNaN(number)) {
    return `${value}원`;
  }

  return `${number.toLocaleString("ko-KR")}원`;
}

function formatAccountNumber(accountNumber) {
  if (!accountNumber) {
    return "-";
  }

  const value = String(accountNumber).replace(/\D/g, "");

  if (value.length === 12) {
    return `${value.slice(0, 4)}-${value.slice(4, 8)}-${value.slice(8)}`;
  }

  return accountNumber;
}

function AccountCard({ account }) {
  if (!account) {
    return (
      <div className="account-card">
        <p>계좌 정보가 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="account-card">
      <h2>내 계좌</h2>

      <div>
        <strong>계좌번호</strong>
        <p>{formatAccountNumber(account.account_number)}</p>
      </div>

      <div>
        <strong>현재 잔액</strong>
        <p>{formatMoney(account.balance)}</p>
      </div>

      <div>
        <strong>계좌 개설일</strong>
        <p>
          {account.opened_at
            ? new Date(account.opened_at).toLocaleString("ko-KR")
            : "-"}
        </p>
      </div>
    </div>
  );
}

export default AccountCard;