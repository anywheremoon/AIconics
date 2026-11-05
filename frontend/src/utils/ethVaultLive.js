import {
  BrowserProvider,
  JsonRpcProvider,
  Contract,
  ZeroAddress,
  getAddress,
  parseEther,
} from "ethers";

import abi from "../contracts/EthRiskVault.abi.json";

const CHAIN_ID = Number(
  import.meta.env.VITE_ETH_VAULT_CHAIN_ID
);

const ADDRESS =
  import.meta.env.VITE_ETH_VAULT_CONTRACT_ADDRESS;

const DEPLOYMENT_ID =
  import.meta.env.VITE_ETH_VAULT_DEPLOYMENT_ID;

async function connection(write = false) {
  if (!window.ethereum) {
    throw new Error("MetaMask가 필요합니다.");
  }

  if (CHAIN_ID !== 31337 || !ADDRESS || !DEPLOYMENT_ID) {
    throw new Error("로컬 Vault 연결 설정을 확인하세요.");
  }

  const provider = new BrowserProvider(window.ethereum);
  const network = await provider.getNetwork();

  if (Number(network.chainId) !== CHAIN_ID) {
    throw new Error("MetaMask를 AIconics Local로 변경하세요.");
  }

  const address = getAddress(ADDRESS);

  if (await provider.getCode(address) === "0x") {
    throw new Error("설정한 주소에 컨트랙트가 없습니다.");
  }

  const runner = write
    ? await provider.getSigner()
    : provider;

  return {
    provider,
    contract: new Contract(address, abi, runner),
    runner,
  };
}

export async function readLiveTransfer(requestId) {
  const rpcUrl = import.meta.env.VITE_ETH_VAULT_RPC_URL;

  if (
    !rpcUrl ||
    CHAIN_ID !== 31337 ||
    !ADDRESS ||
    !DEPLOYMENT_ID
  ) {
    throw new Error("로컬 Vault 조회 설정을 확인하세요.");
  }

  // MetaMask 조회 경로와 분리하고 ethers의 요청 캐시를 끈다.
  const provider = new JsonRpcProvider(
    rpcUrl,
    undefined,
    {
      cacheTimeout: -1,
      batchMaxCount: 1,
    }
  );

  try {
    const actualChainId = Number(
      await provider.send("eth_chainId", [])
    );

    if (actualChainId !== CHAIN_ID) {
      throw new Error(
        `조회 노드의 체인 ID가 다릅니다: ${actualChainId}`
      );
    }

    const address = getAddress(ADDRESS);

    // 최신 블록 번호를 직접 가져와 그 블록의 상태를 조회한다.
    const blockHex = await provider.send(
      "eth_blockNumber",
      []
    );
    const blockTag = Number(BigInt(blockHex));

    const code = await provider.getCode(
      address,
      blockTag
    );

    if (code === "0x") {
      throw new Error(
        "조회 노드의 설정 주소에 컨트랙트가 없습니다."
      );
    }

    const contract = new Contract(
      address,
      abi,
      provider
    );

    const row = await contract.getTransfer(
      requestId,
      { blockTag }
    );

    return {
      requestId,
      sender: row.sender,
      recipient: row.recipient,
      amountWei: row.amount.toString(),
      riskLevel: Number(row.riskLevel),
      status: Number(row.status),
      createdAt: Number(row.createdAt),
      riskScore: Number(row.riskScore),
      requiresAuth: row.requiresAuth,
      requiresAdminApproval: row.requiresAdminApproval,
      authCompleted: row.authCompleted,
      adminApproved: row.adminApproved,
      timelockUntil: Number(row.timelockUntil),
      readBlockNumber: blockTag,
    };
  } finally {
    provider.destroy();
  }
}

export async function requestLiveTransfer({
  sender,
  recipient,
  amount,
}) {
  const { provider, contract, runner } = await connection(true);

  const actualSender = await runner.getAddress();
  const target = getAddress(recipient);
  const value = parseEther(amount);

  if (actualSender.toLowerCase() !== sender.toLowerCase()) {
    throw new Error("선택한 MetaMask 계정이 변경되었습니다.");
  }

  if (
    target === ZeroAddress ||
    target.toLowerCase() === actualSender.toLowerCase()
  ) {
    throw new Error("수신 주소를 확인하세요.");
  }

  if (value <= 0n) {
    throw new Error("송금액은 0보다 커야 합니다.");
  }

  const tx = await contract.requestTransfer(target, { value });
  const receipt = await tx.wait();

  if (!receipt || receipt.status !== 1) {
    throw new Error("예치 거래가 완료되지 않았습니다.");
  }

  let requested;

  for (const log of receipt.logs) {
    if (log.address.toLowerCase() !== ADDRESS.toLowerCase()) {
      continue;
    }

    try {
      const event = contract.interface.parseLog(log);
      if (event?.name === "TransferRequested") {
        requested = event.args;
        break;
      }
    } catch {
      // 다른 이벤트는 건너뛴다.
    }
  }

  if (!requested) {
    throw new Error(
      `예치 후 이벤트를 읽지 못했습니다. 재예치하지 마세요. TX: ${receipt.hash}`
    );
  }

  const block = await provider.getBlock(receipt.blockNumber);

  return {
    requestId: requested.requestId,
    sender: requested.sender,
    recipient: requested.recipient,
    amountWei: requested.amount.toString(),
    chainId: CHAIN_ID,
    verifyingContract: getAddress(ADDRESS),
    deploymentId: DEPLOYMENT_ID,
    depositTxHash: receipt.hash,
    createdAt: Number(block.timestamp),
  };
}

export async function executeLiveTransfer(requestId) {
  const { contract } = await connection(true);
  const tx = await contract.executeTransfer(requestId);
  const receipt = await tx.wait();

  if (!receipt || receipt.status !== 1) {
    throw new Error("송금 실행에 실패했습니다.");
  }

  return receipt.hash;
}

export async function approveLiveTransfer(requestId) {
  const { contract, runner } = await connection(true);

  const signerAddress = await runner.getAddress();
  const owner = await contract.owner();

  if (signerAddress.toLowerCase() !== owner.toLowerCase()) {
    throw new Error(
      `컨트랙트 소유자 지갑으로 전환하세요: ${owner}`
    );
  }

  const row = await contract.getTransfer(requestId);

  if (
    Number(row.riskLevel) !== 2 ||
    !row.requiresAdminApproval
  ) {
    throw new Error("관리자 승인 대상 HIGH 거래가 아닙니다.");
  }

  if (
    Number(row.status) !== 2 ||
    !row.authCompleted
  ) {
    throw new Error(
      "온체인 추가 인증 완료 후 승인할 수 있습니다."
    );
  }

  if (row.adminApproved) {
    throw new Error("이미 승인된 거래입니다.");
  }

  const tx = await contract.approveTransfer(requestId);
  const receipt = await tx.wait();

  if (!receipt || receipt.status !== 1) {
    throw new Error("관리자 승인 거래가 실패했습니다.");
  }

  return receipt.hash;
}