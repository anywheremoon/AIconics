export function isEthAddress(value) {
  return /^0x[0-9a-fA-F]{40}$/.test(value);
}

export function validateVaultInput({ sender, recipient, amount }) {
  if (!isEthAddress(sender)) {
    throw new Error("유효한 송신 지갑 주소를 입력하세요.");
  }

  if (!isEthAddress(recipient)) {
    throw new Error("유효한 수신 지갑 주소를 입력하세요.");
  }

  if (sender.toLowerCase() === recipient.toLowerCase()) {
    throw new Error("송신 주소와 수신 주소는 달라야 합니다.");
  }

  if (!/^(0|[1-9]\d*)(\.\d{1,18})?$/.test(amount)) {
    throw new Error("ETH 금액은 소수점 18자리 이내로 입력하세요.");
  }

  const [whole, fraction = ""] = amount.split(".");
  const wei = BigInt(whole) * 10n ** 18n
    + BigInt(fraction.padEnd(18, "0"));

  if (wei <= 0n || wei > 2n ** 256n - 1n) {
    throw new Error("유효한 양수 ETH 금액을 입력하세요.");
  }
}

export function getExecutionBlockReason(row, now = Date.now()) {
  if (row.status !== "PENDING") return "종료된 거래";
  if (now >= row.expiresAt) return "거래 만료";
  if (row.riskLevel === "CRITICAL") return "CRITICAL 실행 차단";

  if (row.riskLevel === "MEDIUM" && !row.authCompleted) {
    return "추가 인증 필요";
  }

  if (row.riskLevel === "HIGH" && !row.adminApproved) {
    return "관리자 승인 필요";
  }

  if (now < row.unlockAt) return "타임락 대기";

  return "";
}

export function shortAddress(address) {
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

// 실제 컨트랙트 호출은 B의 최종 ABI와 배포 주소를 받은 후 구현합니다.
// 함수 이름만 보고 인자나 payable 값을 추측해서 연결하면 안 됩니다.