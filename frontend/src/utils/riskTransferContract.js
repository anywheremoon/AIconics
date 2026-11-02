// 반드시 B가 제공한 실제 ABI와 대조해야 함.
const RISK_TRANSFER_ABI = [
  "function executeTransfer((address sender,address recipient,uint256 amount,uint256 riskScore,uint8 riskLevel,bytes32 requestId,uint256 deadline,bytes32 nonce) transfer,bytes signature)",
];

const TOKEN_ABI = [
  "function decimals() view returns (uint8)",
  "function symbol() view returns (string)",
  "function allowance(address owner,address spender) view returns (uint256)",
  "function approve(address spender,uint256 amount) returns (bool)",
];

export function isAddress(value) {
  return /^0x[0-9a-fA-F]{40}$/.test(value);
}

export function amountToUnits(value, decimals) {
  if (!/^\d+(\.\d+)?$/.test(value)) {
    throw new Error("송금 금액을 숫자로 입력해 주세요.");
  }

  const [whole, fraction = ""] = value.split(".");

  if (fraction.length > decimals) {
    throw new Error(`소수점은 최대 ${decimals}자리까지 입력할 수 있습니다.`);
  }

  const amount = BigInt(whole + fraction.padEnd(decimals, "0"));

  if (amount <= 0n) {
    throw new Error("송금 금액은 0보다 커야 합니다.");
  }

  if (amount >= 2n ** 256n) {
    throw new Error("송금 금액이 허용 범위를 초과했습니다.");
  }

  return amount.toString();
}

async function loadEthers() {
  // Mock 모드에서는 이 함수를 호출하지 않습니다.
  const packageName = "ethers";

  try {
    return await import(/* @vite-ignore */ packageName);
  } catch {
    throw new Error(
      "실제 지갑 연동에 필요한 ethers 설정을 확인해 주세요."
    );
  }
}

export async function getTokenInfo(tokenAddress) {
  if (!window.ethereum) {
    throw new Error("MetaMask를 설치해 주세요.");
  }

  if (!isAddress(tokenAddress)) {
    throw new Error("테스트 토큰 주소 설정을 확인해 주세요.");
  }

  const { BrowserProvider, Contract } = await loadEthers();
  const provider = new BrowserProvider(window.ethereum);
  const token = new Contract(tokenAddress, TOKEN_ABI, provider);

  const decimals = Number(await token.decimals());
  const symbol = await token.symbol().catch(() => "TOKEN");

  return { decimals, symbol };
}

export function validateAnalysis(data, expected, requireSignature = true) {
  const transfer = data?.transfer;

  if (!transfer) {
    throw new Error("위험 분석 응답에 거래 정보가 없습니다.");
  }

  const sameAddress = (a, b) =>
    isAddress(a) &&
    isAddress(b) &&
    a.toLowerCase() === b.toLowerCase();

  if (
    !sameAddress(transfer.sender, expected.sender) ||
    !sameAddress(transfer.recipient, expected.recipient) ||
    !sameAddress(
      transfer.verifyingContract,
      expected.verifyingContract
    ) ||
    transfer.amount !== expected.amount ||
    Number(transfer.chainId) !== expected.chainId
  ) {
    throw new Error("위험 분석 결과가 요청한 거래 정보와 다릅니다.");
  }

  if (
    !Number.isInteger(transfer.riskLevel) ||
    transfer.riskLevel < 0 ||
    transfer.riskLevel > 3
  ) {
    throw new Error("위험 등급 형식이 올바르지 않습니다.");
  }

  if (
    !Number.isInteger(transfer.riskScore) ||
    transfer.riskScore < 0 ||
    transfer.riskScore > 100
  ) {
    throw new Error("위험 점수 형식이 올바르지 않습니다.");
  }

  if (
    !Number.isSafeInteger(transfer.deadline) ||
    transfer.deadline <= Math.floor(Date.now() / 1000)
  ) {
    throw new Error("거래 승인 시간이 만료되었습니다. 다시 분석해 주세요.");
  }

  const bytes32Pattern = /^0x[0-9a-fA-F]{64}$/;

  if (
    !bytes32Pattern.test(transfer.requestId) ||
    !bytes32Pattern.test(transfer.nonce)
  ) {
    throw new Error("거래 식별자 형식이 올바르지 않습니다.");
  }

  if (
    requireSignature &&
    transfer.riskLevel === 0 &&
    !/^0x[0-9a-fA-F]{130}$/.test(data.signature || "")
  ) {
    throw new Error("LOW 거래의 전자서명이 없거나 형식이 잘못되었습니다.");
  }

  return transfer;
}

export async function executeRiskTransfer({
  analysis,
  expected,
  tokenAddress,
  contractAddress,
  onStage,
}) {
  const transfer = validateAnalysis(analysis, expected);

  if (transfer.riskLevel !== 0) {
    throw new Error("LOW 등급 거래만 송금할 수 있습니다.");
  }

  const { BrowserProvider, Contract } = await loadEthers();

  async function getCheckedSigner() {
    const provider = new BrowserProvider(window.ethereum);
    const signer = await provider.getSigner();
    const account = await signer.getAddress();
    const network = await provider.getNetwork();

    if (account.toLowerCase() !== expected.sender.toLowerCase()) {
      throw new Error("연결 계정이 변경되었습니다. 다시 분석해 주세요.");
    }

    if (Number(network.chainId) !== expected.chainId) {
      throw new Error("네트워크가 변경되었습니다. 다시 분석해 주세요.");
    }

    return signer;
  }

  let signer = await getCheckedSigner();
  const token = new Contract(tokenAddress, TOKEN_ABI, signer);
  const amount = BigInt(transfer.amount);

  const allowance = await token.allowance(
    transfer.sender,
    contractAddress
  );

  if (allowance < amount) {
    onStage("토큰 사용 승인 요청");

    const approval = await token.approve(contractAddress, amount);

    onStage("토큰 사용 승인 확인 중");
    const approvalReceipt = await approval.wait();

    if (!approvalReceipt || approvalReceipt.status !== 1) {
      throw new Error("토큰 사용 승인이 완료되지 않았습니다.");
    }
  }

  // 승인 대기 중 계정·네트워크·만료 시각이 바뀌었는지 다시 확인합니다.
  signer = await getCheckedSigner();
  validateAnalysis(analysis, expected);

  const contract = new Contract(
    contractAddress,
    RISK_TRANSFER_ABI,
    signer
  );

  // chainId와 verifyingContract는 도메인 정보이므로 tuple에서 제외합니다.
  const tuple = [
    transfer.sender,
    transfer.recipient,
    transfer.amount,
    transfer.riskScore,
    transfer.riskLevel,
    transfer.requestId,
    transfer.deadline,
    transfer.nonce,
  ];

  onStage("송금 서명 요청");

  const transaction = await contract.executeTransfer(
    tuple,
    analysis.signature
  );

  onStage("블록체인 송금 확인 중");

  const receipt = await transaction.wait();

  if (!receipt || receipt.status !== 1) {
    throw new Error("블록체인 송금이 완료되지 않았습니다.");
  }

  return { transactionHash: receipt.hash };
}