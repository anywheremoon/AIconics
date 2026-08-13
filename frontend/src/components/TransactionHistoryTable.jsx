//거래 내역을 표 형태로 표시
function formatMoney(value) {
  const number = Number(value);

  if (Number.isNaN(number)) {
    return value;
  }

  return number.toLocaleString("ko-KR");
}

function TransactionHistoryTable({
  transactions = [],
  myAccountId,
  myAccountNumber,
}) {
  if (!transactions.length) {
    return <p>거래 내역이 없습니다.</p>;
  }

  const getTransactionInfo = (transaction) => {
    const type = transaction.transaction_type;

    if (type === "WITHDRAW") {
      return {
        direction: "출금",
        otherAccount: "-",
      };
    }

    const senderId = transaction.sender_account_id;
    const recipientId = transaction.recipient_account_id;

    const isSender =
      senderId !== undefined &&
      Number(senderId) === Number(myAccountId);

    const senderNumber =
      transaction.sender_account_number ||
      transaction.senderAccountNumber;

    const recipientNumber =
      transaction.recipient_account_number ||
      transaction.recipientAccountNumber;

    if (
      senderNumber &&
      String(senderNumber) === String(myAccountNumber)
    ) {
      return {
        direction: "송금",
        otherAccount: recipientNumber || "-",
      };
    }

    if (
      recipientNumber &&
      String(recipientNumber) === String(myAccountNumber)
    ) {
      return {
        direction: "입금",
        otherAccount: senderNumber || "-",
      };
    }

    if (isSender) {
      return {
        direction: "송금",
        otherAccount:
          recipientNumber ||
          transaction.recipient_account_id ||
          "-",
      };
    }

    if (
      recipientId !== undefined &&
      Number(recipientId) === Number(myAccountId)
    ) {
      return {
        direction: "입금",
        otherAccount:
          senderNumber ||
          transaction.sender_account_id ||
          "-",
      };
    }

    return {
      direction: type || "-",
      otherAccount: "-",
    };
  };

  return (
    <table>
      <thead>
        <tr>
          <th>거래 일시</th>
          <th>구분</th>
          <th>상대 계좌</th>
          <th>금액</th>
          <th>상태</th>
        </tr>
      </thead>

      <tbody>
        {transactions.map((transaction) => {
          const info = getTransactionInfo(transaction);

          return (
            <tr key={transaction.id || transaction.request_id}>
              <td>
                {transaction.created_at
                  ? new Date(
                      transaction.created_at
                    ).toLocaleString("ko-KR")
                  : "-"}
              </td>

              <td>{info.direction}</td>

              <td>{info.otherAccount}</td>

              <td>
                {formatMoney(transaction.amount)}
                원
              </td>

              <td>{transaction.status || "-"}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export default TransactionHistoryTable;