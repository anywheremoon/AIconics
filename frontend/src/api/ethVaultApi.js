const STORAGE_KEY = "aiconics_eth_vault_mock_v1";

export const ETH_VAULT_MOCK = true;

export const RISK_POLICY = {
  LOW: { score: 20, delaySeconds: 0 },
  MEDIUM: { score: 50, delaySeconds: 10 },
  HIGH: { score: 75, delaySeconds: 20 },
  CRITICAL: { score: 90, delaySeconds: 0 },
};

function readTransfers() {
  const raw = localStorage.getItem(STORAGE_KEY);

  if (!raw) return [];

  try {
    const rows = JSON.parse(raw);
    return Array.isArray(rows) ? rows : [];
  } catch {
    throw new Error("Mock 저장 데이터가 손상되었습니다.");
  }
}

function saveTransfers(rows) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(rows));
}

function updateTransfer(id, updater) {
  const rows = readTransfers();
  const index = rows.findIndex((row) => row.id === id);

  if (index < 0) {
    throw new Error("거래를 찾을 수 없습니다.");
  }

  const updated = updater(rows[index]);
  rows[index] = updated;
  saveTransfers(rows);

  return updated;
}

function requirePending(row) {
  if (row.status !== "PENDING") {
    throw new Error("이미 종료된 거래입니다.");
  }

  if (Date.now() >= row.expiresAt) {
    throw new Error("만료된 거래입니다. 만료 취소를 진행하세요.");
  }
}

export async function listVaultTransfers() {
  return readTransfers();
}

export async function createVaultTransfer({
  sender,
  recipient,
  amount,
  riskLevel,
}) {
  const policy = RISK_POLICY[riskLevel];

  if (!policy) throw new Error("지원하지 않는 위험 등급입니다.");

  const now = Date.now();

  const row = {
    id: crypto.randomUUID(),
    sender,
    recipient,
    amount,
    riskLevel,
    riskScore: policy.score,
    status: "PENDING",
    authCompleted: false,
    adminApproved: false,
    createdAt: now,
    unlockAt: now + policy.delaySeconds * 1000,
    expiresAt: now + 10 * 60 * 1000,
    completedAt: null,
  };

  saveTransfers([row, ...readTransfers()]);
  return row;
}

export async function completeVaultAuth(id) {
  return updateTransfer(id, (row) => {
    requirePending(row);

    if (row.riskLevel !== "MEDIUM") {
      throw new Error("추가 인증 대상 거래가 아닙니다.");
    }

    return { ...row, authCompleted: true };
  });
}

export async function approveVaultTransfer(id) {
  return updateTransfer(id, (row) => {
    requirePending(row);

    if (row.riskLevel !== "HIGH") {
      throw new Error("관리자 승인 대상 거래가 아닙니다.");
    }

    return { ...row, adminApproved: true };
  });
}

export async function rejectVaultTransfer(id) {
  return updateTransfer(id, (row) => {
    requirePending(row);

    return {
      ...row,
      status: "REFUNDED",
      completedAt: Date.now(),
    };
  });
}

export async function executeVaultTransfer(id) {
  return updateTransfer(id, (row) => {
    requirePending(row);

    if (row.riskLevel === "CRITICAL") {
      throw new Error("CRITICAL 거래는 실행할 수 없습니다.");
    }

    if (row.riskLevel === "MEDIUM" && !row.authCompleted) {
      throw new Error("추가 인증이 필요합니다.");
    }

    if (row.riskLevel === "HIGH" && !row.adminApproved) {
      throw new Error("관리자 승인이 필요합니다.");
    }

    if (Date.now() < row.unlockAt) {
      throw new Error("타임락 대기 시간이 남아 있습니다.");
    }

    return {
      ...row,
      status: "EXECUTED",
      completedAt: Date.now(),
    };
  });
}

export async function cancelExpiredVaultTransfer(id) {
  return updateTransfer(id, (row) => {
    if (row.status !== "PENDING") {
      throw new Error("이미 종료된 거래입니다.");
    }

    if (Date.now() < row.expiresAt) {
      throw new Error("아직 만료되지 않았습니다.");
    }

    return {
      ...row,
      status: "CANCELLED",
      completedAt: Date.now(),
    };
  });
}