
import { expect } from "chai";
import { network } from "hardhat";

describe("EthRiskVault", function () {
  it("ETH 송금 요청을 생성하고 예치한다", async function () {
    const { ethers } = await network.connect();
    const [owner, sender, recipient] = await ethers.getSigners();

    const Vault = await ethers.getContractFactory("EthRiskVault");
    const vault = await Vault.deploy(owner.address, owner.address);
    await vault.waitForDeployment();

    const amount = ethers.parseEther("1");

    await expect(
      vault.connect(sender).requestTransfer(recipient.address, {
        value: amount,
      })
    ).to.emit(vault, "TransferRequested");

    expect(await ethers.provider.getBalance(await vault.getAddress()))
      .to.equal(amount);

    expect(await vault.nextRequestId()).to.equal(1n);
  });

it("잘못된 AI 서명은 거부한다", async function () {
  const { ethers } = await network.connect();
  const [owner, sender, recipient, attacker] =
    await ethers.getSigners();

  const Vault = await ethers.getContractFactory("EthRiskVault");
  const vault = await Vault.deploy(owner.address, owner.address);
  await vault.waitForDeployment();

  const amount = ethers.parseEther("1");

  await vault.connect(sender).requestTransfer(recipient.address, {
    value: amount,
  });

  const block = await ethers.provider.getBlock("latest");
  const deadline = BigInt(block!.timestamp + 300);

  const result = {
    requestId: ethers.ZeroHash,
    sender: sender.address,
    recipient: recipient.address,
    amount,
    riskScore: 10n,
    riskLevel: 0,
    requiresAuth: false,
    requiresAdminApproval: false,
    timelockUntil: 0n,
    deadline,
    analysisHash: ethers.id("test-analysis"),
    nonce: ethers.id("test-nonce"),
  };

  const domain = {
    name: "AIconics EthRiskVault",
    version: "1",
    chainId: (await ethers.provider.getNetwork()).chainId,
    verifyingContract: await vault.getAddress(),
  };

  const types = {
    RiskResult: [
      { name: "requestId", type: "bytes32" },
      { name: "sender", type: "address" },
      { name: "recipient", type: "address" },
      { name: "amount", type: "uint256" },
      { name: "riskScore", type: "uint256" },
      { name: "riskLevel", type: "uint8" },
      { name: "requiresAuth", type: "bool" },
      { name: "requiresAdminApproval", type: "bool" },
      { name: "timelockUntil", type: "uint256" },
      { name: "deadline", type: "uint256" },
      { name: "analysisHash", type: "bytes32" },
      { name: "nonce", type: "bytes32" },
    ],
  };

  // 등록된 riskSigner가 아닌 공격자 계정으로 서명
  const invalidSignature = await attacker.signTypedData(
    domain,
    types,
    result
  );

  await expect(
    vault.submitRiskResult(result, invalidSignature)
  ).to.be.revertedWith("Invalid signature");
});

it("LOW 거래는 정상 서명 후 ETH 송금에 성공한다", async function () {
  const { ethers } = await network.connect();
  const [owner, sender, recipient] = await ethers.getSigners();

  const Vault = await ethers.getContractFactory("EthRiskVault");
  const vault = await Vault.deploy(owner.address, owner.address);
  await vault.waitForDeployment();

  const amount = ethers.parseEther("1");

  await vault.connect(sender).requestTransfer(recipient.address, {
    value: amount,
  });

  const block = await ethers.provider.getBlock("latest");

  const result = {
    requestId: ethers.ZeroHash,
    sender: sender.address,
    recipient: recipient.address,
    amount,
    riskScore: 10n,
    riskLevel: 0,
    requiresAuth: false,
    requiresAdminApproval: false,
    timelockUntil: 0n,
    deadline: BigInt(block!.timestamp + 300),
    analysisHash: ethers.id("low-analysis"),
    nonce: ethers.id("low-nonce"),
  };

  const domain = {
    name: "AIconics EthRiskVault",
    version: "1",
    chainId: (await ethers.provider.getNetwork()).chainId,
    verifyingContract: await vault.getAddress(),
  };

  const types = {
    RiskResult: [
      { name: "requestId", type: "bytes32" },
      { name: "sender", type: "address" },
      { name: "recipient", type: "address" },
      { name: "amount", type: "uint256" },
      { name: "riskScore", type: "uint256" },
      { name: "riskLevel", type: "uint8" },
      { name: "requiresAuth", type: "bool" },
      { name: "requiresAdminApproval", type: "bool" },
      { name: "timelockUntil", type: "uint256" },
      { name: "deadline", type: "uint256" },
      { name: "analysisHash", type: "bytes32" },
      { name: "nonce", type: "bytes32" },
    ],
  };

  const signature = await owner.signTypedData(domain, types, result);

  await vault.submitRiskResult(result, signature);

  const balanceBefore = await ethers.provider.getBalance(
    recipient.address
  );

  await expect(vault.executeTransfer(ethers.ZeroHash))
    .to.emit(vault, "TransferExecuted");

  const balanceAfter = await ethers.provider.getBalance(
    recipient.address
  );

  expect(balanceAfter - balanceBefore).to.equal(amount);

  expect(
    await ethers.provider.getBalance(await vault.getAddress())
  ).to.equal(0n);
});

it("MEDIUM 거래는 추가 인증 후 송금할 수 있다", async function () {
  const { ethers } = await network.connect();
  const [owner, sender, recipient, attacker] =
    await ethers.getSigners();

  const Vault = await ethers.getContractFactory("EthRiskVault");
  const vault = await Vault.deploy(owner.address, owner.address);
  await vault.waitForDeployment();

  const amount = ethers.parseEther("1");
  const requestId = ethers.ZeroHash;

  await vault.connect(sender).requestTransfer(recipient.address, {
    value: amount,
  });

  const block = await ethers.provider.getBlock("latest");

  const result = {
    requestId,
    sender: sender.address,
    recipient: recipient.address,
    amount,
    riskScore: 50n,
    riskLevel: 1,
    requiresAuth: true,
    requiresAdminApproval: false,
    timelockUntil: 0n,
    deadline: BigInt(block!.timestamp + 300),
    analysisHash: ethers.id("medium-analysis"),
    nonce: ethers.id("medium-nonce"),
  };

  const domain = {
    name: "AIconics EthRiskVault",
    version: "1",
    chainId: (await ethers.provider.getNetwork()).chainId,
    verifyingContract: await vault.getAddress(),
  };

  const types = {
    RiskResult: [
      { name: "requestId", type: "bytes32" },
      { name: "sender", type: "address" },
      { name: "recipient", type: "address" },
      { name: "amount", type: "uint256" },
      { name: "riskScore", type: "uint256" },
      { name: "riskLevel", type: "uint8" },
      { name: "requiresAuth", type: "bool" },
      { name: "requiresAdminApproval", type: "bool" },
      { name: "timelockUntil", type: "uint256" },
      { name: "deadline", type: "uint256" },
      { name: "analysisHash", type: "bytes32" },
      { name: "nonce", type: "bytes32" },
    ],
  };

  const signature = await owner.signTypedData(domain, types, result);
  await vault.submitRiskResult(result, signature);

  // 인증 전에는 송금 불가
  await expect(
    vault.executeTransfer(requestId)
  ).to.be.revertedWith("Auth required");

  // 권한 없는 계정은 인증 완료 처리 불가
  await expect(
    vault.connect(attacker).completeAuth(requestId)
  ).to.be.revertedWith("Not authorized");

  // 인증 담당자가 인증 완료 처리
  await vault.completeAuth(requestId);

  const balanceBefore = await ethers.provider.getBalance(
    recipient.address
  );

  await expect(vault.executeTransfer(requestId))
    .to.emit(vault, "TransferExecuted");

  const balanceAfter = await ethers.provider.getBalance(
    recipient.address
  );

  expect(balanceAfter - balanceBefore).to.equal(amount);
});

it("HIGH 거래는 인증, 관리자 승인, 타임락 이후 송금된다", async function () {
  const { ethers } = await network.connect();
  const [owner, sender, recipient, attacker] =
    await ethers.getSigners();

  const Vault = await ethers.getContractFactory("EthRiskVault");
  const vault = await Vault.deploy(owner.address, owner.address);
  await vault.waitForDeployment();

  const amount = ethers.parseEther("1");
  const requestId = ethers.ZeroHash;

  await vault.connect(sender).requestTransfer(recipient.address, {
    value: amount,
  });

  const block = await ethers.provider.getBlock("latest");
  const timelockUntil = BigInt(block!.timestamp + 3600);

  const result = {
    requestId,
    sender: sender.address,
    recipient: recipient.address,
    amount,
    riskScore: 85n,
    riskLevel: 2,
    requiresAuth: true,
    requiresAdminApproval: true,
    timelockUntil,
    deadline: BigInt(block!.timestamp + 300),
    analysisHash: ethers.id("high-analysis"),
    nonce: ethers.id("high-nonce"),
  };

  const domain = {
    name: "AIconics EthRiskVault",
    version: "1",
    chainId: (await ethers.provider.getNetwork()).chainId,
    verifyingContract: await vault.getAddress(),
  };

  const types = {
    RiskResult: [
      { name: "requestId", type: "bytes32" },
      { name: "sender", type: "address" },
      { name: "recipient", type: "address" },
      { name: "amount", type: "uint256" },
      { name: "riskScore", type: "uint256" },
      { name: "riskLevel", type: "uint8" },
      { name: "requiresAuth", type: "bool" },
      { name: "requiresAdminApproval", type: "bool" },
      { name: "timelockUntil", type: "uint256" },
      { name: "deadline", type: "uint256" },
      { name: "analysisHash", type: "bytes32" },
      { name: "nonce", type: "bytes32" },
    ],
  };

  const signature = await owner.signTypedData(domain, types, result);
  await vault.submitRiskResult(result, signature);

  // 추가 인증 전에는 송금 불가
  await expect(
    vault.executeTransfer(requestId)
  ).to.be.revertedWith("Auth required");

  await vault.completeAuth(requestId);

  // 관리자 승인 전에는 송금 불가
  await expect(
    vault.executeTransfer(requestId)
  ).to.be.revertedWith("Admin approval required");

  // 일반 사용자는 승인 불가
  await expect(
    vault.connect(attacker).approveTransfer(requestId)
  ).to.be.revertedWithCustomError(vault, "OwnableUnauthorizedAccount")
    .withArgs(attacker.address);

  await vault.approveTransfer(requestId);

  // 승인 후에도 타임락이 끝나기 전에는 송금 불가
  await expect(
    vault.executeTransfer(requestId)
  ).to.be.revertedWith("Timelock active");

  // 테스트 블록체인 시간을 1시간 이후로 이동
  await ethers.provider.send("evm_setNextBlockTimestamp", [
    Number(timelockUntil),
  ]);
  await ethers.provider.send("evm_mine", []);

  const balanceBefore = await ethers.provider.getBalance(
    recipient.address
  );

  await expect(vault.executeTransfer(requestId))
    .to.emit(vault, "TransferExecuted");

  const balanceAfter = await ethers.provider.getBalance(
    recipient.address
  );

  expect(balanceAfter - balanceBefore).to.equal(amount);
});

it("CRITICAL 거래는 차단되고 ETH가 환불된다", async function () {
  const { ethers } = await network.connect();
  const [owner, sender, recipient] = await ethers.getSigners();

  const Vault = await ethers.getContractFactory("EthRiskVault");
  const vault = await Vault.deploy(owner.address, owner.address);
  await vault.waitForDeployment();

  const amount = ethers.parseEther("1");
  const requestId = ethers.ZeroHash;

  await vault.connect(sender).requestTransfer(recipient.address, {
    value: amount,
  });

  const block = await ethers.provider.getBlock("latest");

  const result = {
    requestId,
    sender: sender.address,
    recipient: recipient.address,
    amount,
    riskScore: 99n,
    riskLevel: 3,
    requiresAuth: true,
    requiresAdminApproval: true,
    timelockUntil: 0n,
    deadline: BigInt(block!.timestamp + 300),
    analysisHash: ethers.id("critical-analysis"),
    nonce: ethers.id("critical-nonce"),
  };

  const domain = {
    name: "AIconics EthRiskVault",
    version: "1",
    chainId: (await ethers.provider.getNetwork()).chainId,
    verifyingContract: await vault.getAddress(),
  };

  const types = {
    RiskResult: [
      { name: "requestId", type: "bytes32" },
      { name: "sender", type: "address" },
      { name: "recipient", type: "address" },
      { name: "amount", type: "uint256" },
      { name: "riskScore", type: "uint256" },
      { name: "riskLevel", type: "uint8" },
      { name: "requiresAuth", type: "bool" },
      { name: "requiresAdminApproval", type: "bool" },
      { name: "timelockUntil", type: "uint256" },
      { name: "deadline", type: "uint256" },
      { name: "analysisHash", type: "bytes32" },
      { name: "nonce", type: "bytes32" },
    ],
  };

  const signature = await owner.signTypedData(domain, types, result);

  const balanceBefore = await ethers.provider.getBalance(sender.address);

  // CRITICAL 분석 결과 제출 시 자동 환불
  await expect(
    vault.submitRiskResult(result, signature)
  ).to.emit(vault, "RiskResultSubmitted");

  const balanceAfter = await ethers.provider.getBalance(sender.address);

  expect(balanceAfter).to.be.greaterThan(balanceBefore);

  // 컨트랙트에 남은 ETH가 없어야 함
  expect(
    await ethers.provider.getBalance(await vault.getAddress())
  ).to.equal(0n);

  // 차단된 거래는 실행할 수 없음
  await expect(
    vault.executeTransfer(requestId)
  ).to.be.revertedWith("No ETH to transfer");
});

it("관리자가 거래를 거절하면 ETH가 환불된다", async function () {
  const { ethers } = await network.connect();
  const [owner, sender, recipient, attacker] =
    await ethers.getSigners();

  const Vault = await ethers.getContractFactory("EthRiskVault");
  const vault = await Vault.deploy(owner.address, owner.address);
  await vault.waitForDeployment();

  const amount = ethers.parseEther("1");
  const requestId = ethers.ZeroHash;

  await vault.connect(sender).requestTransfer(recipient.address, {
    value: amount,
  });

  // 관리자가 아닌 계정은 거래 거절 불가
  await expect(
    vault.connect(attacker).rejectTransfer(requestId)
  ).to.be.revertedWithCustomError(
    vault,
    "OwnableUnauthorizedAccount"
  ).withArgs(attacker.address);

  const balanceBefore = await ethers.provider.getBalance(sender.address);

  // 관리자가 거래 거절
  await expect(
    vault.rejectTransfer(requestId)
  ).to.emit(vault, "TransferRejected");

  const balanceAfter = await ethers.provider.getBalance(sender.address);

  expect(balanceAfter - balanceBefore).to.equal(amount);

  // 환불 후 컨트랙트 잔액 확인
  expect(
    await ethers.provider.getBalance(await vault.getAddress())
  ).to.equal(0n);

  // 환불된 거래는 송금할 수 없음
  await expect(
    vault.executeTransfer(requestId)
  ).to.be.revertedWith("No ETH to transfer");
});

it("24시간이 지난 거래는 취소하고 ETH를 환불받는다", async function () {
  const { ethers } = await network.connect();
  const [owner, sender, recipient, attacker] =
    await ethers.getSigners();

  const Vault = await ethers.getContractFactory("EthRiskVault");
  const vault = await Vault.deploy(owner.address, owner.address);
  await vault.waitForDeployment();

  const amount = ethers.parseEther("1");
  const requestId = ethers.ZeroHash;

  await vault.connect(sender).requestTransfer(recipient.address, {
    value: amount,
  });

  // 만료 전에는 취소 불가
  await expect(
    vault.connect(sender).cancelExpired(requestId)
  ).to.be.revertedWith("Request not expired");

  // 다른 사용자는 취소 불가
  await expect(
    vault.connect(attacker).cancelExpired(requestId)
  ).to.be.revertedWith("Not sender");

  // 테스트 블록체인의 시간을 24시간 이후로 이동
  const block = await ethers.provider.getBlock("latest");

  await ethers.provider.send("evm_setNextBlockTimestamp", [
    block!.timestamp + 86401,
  ]);
  await ethers.provider.send("evm_mine", []);

  const balanceBefore = await ethers.provider.getBalance(sender.address);

  // 송금자가 만료된 거래 취소
  const tx = await vault.connect(sender).cancelExpired(requestId);
  const receipt = await tx.wait();

  await expect(tx).to.emit(vault, "TransferCancelled");

  const balanceAfter = await ethers.provider.getBalance(sender.address);

  // 송금자가 가스비를 부담하므로 환불액에서 가스비를 고려
  const gasCost = receipt!.gasUsed * receipt!.gasPrice;

  expect(balanceAfter - balanceBefore + gasCost).to.equal(amount);

  // 컨트랙트 잔액은 0
  expect(
    await ethers.provider.getBalance(await vault.getAddress())
  ).to.equal(0n);

  // 취소된 거래는 다시 실행할 수 없음
  await expect(
    vault.executeTransfer(requestId)
  ).to.be.revertedWith("No ETH to transfer");

  // 중복 취소도 불가
  await expect(
    vault.connect(sender).cancelExpired(requestId)
  ).to.be.revertedWith("No ETH to refund");
});

it("이미 실행된 거래는 중복 송금할 수 없다", async function () {
  const { ethers } = await network.connect();
  const [owner, sender, recipient] = await ethers.getSigners();

  const Vault = await ethers.getContractFactory("EthRiskVault");
  const vault = await Vault.deploy(owner.address, owner.address);
  await vault.waitForDeployment();

  const amount = ethers.parseEther("1");
  const requestId = ethers.ZeroHash;

  await vault.connect(sender).requestTransfer(recipient.address, {
    value: amount,
  });

  const block = await ethers.provider.getBlock("latest");

  const result = {
    requestId,
    sender: sender.address,
    recipient: recipient.address,
    amount,
    riskScore: 10n,
    riskLevel: 0,
    requiresAuth: false,
    requiresAdminApproval: false,
    timelockUntil: 0n,
    deadline: BigInt(block!.timestamp + 300),
    analysisHash: ethers.id("duplicate-analysis"),
    nonce: ethers.id("duplicate-nonce"),
  };

  const domain = {
    name: "AIconics EthRiskVault",
    version: "1",
    chainId: (await ethers.provider.getNetwork()).chainId,
    verifyingContract: await vault.getAddress(),
  };

  const types = {
    RiskResult: [
      { name: "requestId", type: "bytes32" },
      { name: "sender", type: "address" },
      { name: "recipient", type: "address" },
      { name: "amount", type: "uint256" },
      { name: "riskScore", type: "uint256" },
      { name: "riskLevel", type: "uint8" },
      { name: "requiresAuth", type: "bool" },
      { name: "requiresAdminApproval", type: "bool" },
      { name: "timelockUntil", type: "uint256" },
      { name: "deadline", type: "uint256" },
      { name: "analysisHash", type: "bytes32" },
      { name: "nonce", type: "bytes32" },
    ],
  };

  const signature = await owner.signTypedData(domain, types, result);

  await vault.submitRiskResult(result, signature);

  // 첫 번째 송금은 성공
  await vault.executeTransfer(requestId);

  // 두 번째 송금은 거부
  await expect(
    vault.executeTransfer(requestId)
  ).to.be.revertedWith("No ETH to transfer");

  // 같은 분석 결과와 서명을 다시 제출할 수도 없음
  await expect(
    vault.submitRiskResult(result, signature)
  ).to.be.revertedWith("Invalid status");

  expect(
    await ethers.provider.getBalance(await vault.getAddress())
  ).to.equal(0n);
});

it("서로 다른 거래에서 동일 nonce를 재사용할 수 없다", async function () {
  const { ethers } = await network.connect();
  const [owner, sender, recipient] = await ethers.getSigners();

  const Vault = await ethers.getContractFactory("EthRiskVault");
  const vault = await Vault.deploy(owner.address, owner.address);
  await vault.waitForDeployment();

  const amount = ethers.parseEther("1");
  const nonce = ethers.id("shared-nonce");

  // 두 개의 송금 요청 생성
  await vault.connect(sender).requestTransfer(recipient.address, {
    value: amount,
  });
  await vault.connect(sender).requestTransfer(recipient.address, {
    value: amount,
  });

  const block = await ethers.provider.getBlock("latest");

  const domain = {
    name: "AIconics EthRiskVault",
    version: "1",
    chainId: (await ethers.provider.getNetwork()).chainId,
    verifyingContract: await vault.getAddress(),
  };

  const types = {
    RiskResult: [
      { name: "requestId", type: "bytes32" },
      { name: "sender", type: "address" },
      { name: "recipient", type: "address" },
      { name: "amount", type: "uint256" },
      { name: "riskScore", type: "uint256" },
      { name: "riskLevel", type: "uint8" },
      { name: "requiresAuth", type: "bool" },
      { name: "requiresAdminApproval", type: "bool" },
      { name: "timelockUntil", type: "uint256" },
      { name: "deadline", type: "uint256" },
      { name: "analysisHash", type: "bytes32" },
      { name: "nonce", type: "bytes32" },
    ],
  };

  const firstResult = {
    requestId: ethers.ZeroHash,
    sender: sender.address,
    recipient: recipient.address,
    amount,
    riskScore: 10n,
    riskLevel: 0,
    requiresAuth: false,
    requiresAdminApproval: false,
    timelockUntil: 0n,
    deadline: BigInt(block!.timestamp + 300),
    analysisHash: ethers.id("first-analysis"),
    nonce,
  };

  const firstSignature = await owner.signTypedData(
    domain, types, firstResult
  );

  // 첫 번째 거래에 nonce 사용
  await vault.submitRiskResult(firstResult, firstSignature);

  const secondResult = {
    ...firstResult,
    requestId: ethers.zeroPadValue("0x01", 32),
    analysisHash: ethers.id("second-analysis"),
  };

  const secondSignature = await owner.signTypedData(
    domain, types, secondResult
  );

  // 두 번째 거래에서 같은 nonce 재사용 시 거부
  await expect(
    vault.submitRiskResult(secondResult, secondSignature)
  ).to.be.revertedWith("Nonce already used");

  expect(await vault.usedNonces(nonce)).to.equal(true);
});

});
