import { expect } from "chai";
import { network } from "hardhat";

describe("EthRiskVault security", function () {
  async function setup() {
    const { ethers } = await network.connect();
    const [owner, sender, recipient, attacker] = await ethers.getSigners();
    const Vault = await ethers.getContractFactory("EthRiskVault");
    const vault = await Vault.deploy(owner.address, owner.address);
    await vault.waitForDeployment();

    const amount = ethers.parseEther("1");
    await vault.connect(sender).requestTransfer(recipient.address, { value: amount });
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
      analysisHash: ethers.id("security-analysis"),
      nonce: ethers.id("security-nonce"),
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
    return { ethers, owner, sender, recipient, attacker, vault, amount, result, domain, types, Vault };
  }

  it("서명 이후 분석 결과를 변조하면 거부한다", async function () {
    const { owner, vault, result, domain, types } = await setup();
    const signature = await owner.signTypedData(domain, types, result);
    await expect(
      vault.submitRiskResult({ ...result, riskScore: 99n }, signature)
    ).to.be.revertedWith("Invalid signature");
  });

  it("만료된 서명은 거부한다", async function () {
    const { ethers, owner, vault, result, domain, types } = await setup();
    const signature = await owner.signTypedData(domain, types, result);
    await ethers.provider.send("evm_setNextBlockTimestamp", [Number(result.deadline) + 1]);
    await ethers.provider.send("evm_mine", []);
    await expect(vault.submitRiskResult(result, signature))
      .to.be.revertedWith("Signature expired");
  });

  it("서명된 LOW 결과라도 인증 요구 정책을 위반하면 거부한다", async function () {
    const { owner, vault, result, domain, types } = await setup();
    const invalidPolicy = { ...result, requiresAuth: true };
    const signature = await owner.signTypedData(domain, types, invalidPolicy);
    await expect(vault.submitRiskResult(invalidPolicy, signature))
      .to.be.revertedWith("Invalid LOW policy");
  });

  it("다른 Vault에 발급된 서명을 재사용할 수 없다", async function () {
    const { owner, sender, vault, result, domain, types, Vault } = await setup();
    const otherVault = await Vault.deploy(owner.address, owner.address);
    await otherVault.waitForDeployment();
    const signature = await owner.signTypedData(domain, types, result);
    await otherVault.connect(sender).requestTransfer(result.recipient, {
      value: result.amount,
    });
    await expect(otherVault.submitRiskResult(result, signature))
      .to.be.revertedWith("Invalid signature");
  });

  it("권한 없는 사용자는 인증 완료와 관리자 승인을 할 수 없다", async function () {
    const { attacker, vault, ethers } = await setup();
    await expect(vault.connect(attacker).completeAuth(ethers.ZeroHash))
      .to.be.revertedWith("Not authorized");
    await expect(vault.connect(attacker).approveTransfer(ethers.ZeroHash))
      .to.be.revertedWithCustomError(vault, "OwnableUnauthorizedAccount")
      .withArgs(attacker.address);
  });
  it("재진입 공격으로 ETH를 중복 출금할 수 없다", async function () {
  const { ethers } = await network.connect();
  const [owner, sender] = await ethers.getSigners();

  const Vault = await ethers.getContractFactory("EthRiskVault");
  const vault = await Vault.deploy(owner.address, owner.address);
  await vault.waitForDeployment();

  const Attacker = await ethers.getContractFactory("ReentrancyAttacker");
  const attacker = await Attacker.deploy(await vault.getAddress());
  await attacker.waitForDeployment();

  const amount = ethers.parseEther("1");

  // 공격 컨트랙트가 송금 요청 생성
  await attacker.connect(sender).requestAttack({ value: amount });

  const block = await ethers.provider.getBlock("latest");

  const result = {
    requestId: ethers.ZeroHash,
    sender: await attacker.getAddress(),
    recipient: await attacker.getAddress(),
    amount,
    riskScore: 10n,
    riskLevel: 0,
    requiresAuth: false,
    requiresAdminApproval: false,
    timelockUntil: 0n,
    deadline: BigInt(block!.timestamp + 300),
    analysisHash: ethers.id("reentrancy-analysis"),
    nonce: ethers.id("reentrancy-nonce"),
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

  // ETH 수령 중 재진입 공격 시도
  await attacker.attack();

  expect(await attacker.attackAttempted()).to.equal(true);
  expect(await attacker.attackSucceeded()).to.equal(false);

  // ETH가 한 번만 지급됐는지 확인
  expect(
    await ethers.provider.getBalance(await attacker.getAddress())
  ).to.equal(amount);

  expect(
    await ethers.provider.getBalance(await vault.getAddress())
  ).to.equal(0n);

  // 동일 거래의 재실행도 차단
  await expect(
    vault.executeTransfer(ethers.ZeroHash)
  ).to.be.revertedWith("No ETH to transfer");
});
});
