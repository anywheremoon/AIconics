import type { Contract } from "ethers";
import { describe, it } from "mocha";
import { expect } from "chai";
import { network } from "hardhat";

import "@nomicfoundation/hardhat-toolbox-mocha-ethers";

describe("EthRiskVault security and policy", function () {
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

  async function setup() {
    const { ethers } = await network.connect();
    const [owner, sender, recipient, attacker] =
      await ethers.getSigners();

    const Vault = await ethers.getContractFactory("EthRiskVault");
    const vault = await Vault.deploy(owner.address, owner.address);
    await vault.waitForDeployment();

    const amount = ethers.parseEther("1");
    const senderVault = vault.connect(sender) as Contract;

    await (
      await senderVault.requestTransfer(recipient.address, {
        value: amount,
      })
    ).wait();

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

    return {
      ethers,
      owner,
      sender,
      recipient,
      attacker,
      vault,
      amount,
      result,
      domain,
      Vault,
    };
  }

  it("서명 이후 분석 결과를 변조하면 거부한다", async function () {
    const { owner, vault, result, domain } = await setup();

    const signature = await owner.signTypedData(
      domain,
      types,
      result
    );

    await expect(
      vault.submitRiskResult(
        { ...result, riskScore: 99n },
        signature
      )
    ).to.be.revertedWith("Invalid signature");
  });

  it("만료된 서명은 거부한다", async function () {
    const { ethers, owner, vault, result, domain } = await setup();

    const signature = await owner.signTypedData(
      domain,
      types,
      result
    );

    await ethers.provider.send("evm_setNextBlockTimestamp", [
      Number(result.deadline) + 1,
    ]);
    await ethers.provider.send("evm_mine", []);

    await expect(
      vault.submitRiskResult(result, signature)
    ).to.be.revertedWith("Signature expired");
  });

  it("서명된 LOW 결과라도 인증 요구 정책을 위반하면 거부한다", async function () {
    const { owner, vault, result, domain } = await setup();

    const invalidPolicy = {
      ...result,
      requiresAuth: true,
    };

    const signature = await owner.signTypedData(
      domain,
      types,
      invalidPolicy
    );

    await expect(
      vault.submitRiskResult(invalidPolicy, signature)
    ).to.be.revertedWith("Invalid LOW policy");
  });

  it("다른 Vault에 발급된 서명을 재사용할 수 없다", async function () {
    const {
      owner,
      sender,
      result,
      domain,
      Vault,
    } = await setup();

    const otherVault = await Vault.deploy(
      owner.address,
      owner.address
    );
    await otherVault.waitForDeployment();

    const signature = await owner.signTypedData(
      domain,
      types,
      result
    );

    const otherSenderVault = otherVault.connect(sender) as Contract;

    await (
      await otherSenderVault.requestTransfer(result.recipient, {
        value: result.amount,
      })
    ).wait();

    await expect(
      otherVault.submitRiskResult(result, signature)
    ).to.be.revertedWith("Invalid signature");
  });

  it("권한 없는 사용자는 인증 완료와 관리자 승인을 할 수 없다", async function () {
    const { attacker, vault, ethers } = await setup();
    const unauthorizedVault = vault.connect(attacker) as Contract;

    await expect(
      unauthorizedVault.completeAuth(ethers.ZeroHash)
    ).to.be.revertedWith("Not authorized");

    await expect(
      unauthorizedVault.approveTransfer(ethers.ZeroHash)
    )
      .to.be.revertedWithCustomError(
        vault,
        "OwnableUnauthorizedAccount"
      )
      .withArgs(attacker.address);
  });

  it("재진입 공격으로 ETH를 중복 출금할 수 없다", async function () {
    const { ethers } = await network.connect();
    const [owner, sender] = await ethers.getSigners();

    const Vault = await ethers.getContractFactory("EthRiskVault");
    const vault = await Vault.deploy(owner.address, owner.address);
    await vault.waitForDeployment();

    const Attacker = await ethers.getContractFactory(
      "ReentrancyAttacker"
    );
    const attacker = await Attacker.deploy(
      await vault.getAddress()
    );
    await attacker.waitForDeployment();

    const amount = ethers.parseEther("1");
    const senderAttacker = attacker.connect(sender) as Contract;

    await (
      await senderAttacker.requestAttack({ value: amount })
    ).wait();

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

    const signature = await owner.signTypedData(
      domain,
      types,
      result
    );

    await (
      await vault.submitRiskResult(result, signature)
    ).wait();

    await (await attacker.attack()).wait();

    expect(await attacker.attackAttempted()).to.equal(true);
    expect(await attacker.attackSucceeded()).to.equal(false);

    expect(
      await ethers.provider.getBalance(
        await attacker.getAddress()
      )
    ).to.equal(amount);

    expect(
      await ethers.provider.getBalance(
        await vault.getAddress()
      )
    ).to.equal(0n);

    await expect(
      vault.executeTransfer(ethers.ZeroHash)
    ).to.be.revertedWith("No ETH to transfer");
  });

  it("HIGH: 추가 인증과 관리자 승인 후 대기 없이 송금된다", async function () {
    const {
      ethers,
      owner,
      recipient,
      vault,
      result,
      domain,
    } = await setup();

    const high = {
      ...result,
      riskScore: 75n,
      riskLevel: 2,
      requiresAuth: true,
      requiresAdminApproval: true,
      timelockUntil: 0n,
    };

    const signature = await owner.signTypedData(
      domain,
      types,
      high
    );

    await (
      await vault.submitRiskResult(high, signature)
    ).wait();

    // 추가 인증 전에는 송금 차단
    await expect(
      vault.executeTransfer(high.requestId)
    ).to.be.revertedWith("Auth required");

    await (
      await vault.completeAuth(high.requestId)
    ).wait();

    // 관리자 승인 전에는 송금 차단
    await expect(
      vault.executeTransfer(high.requestId)
    ).to.be.revertedWith("Admin approval required");

    await (
      await vault.approveTransfer(high.requestId)
    ).wait();

    // 시간 이동 없이 즉시 송금
    const before = await ethers.provider.getBalance(
      recipient.address
    );

    await (
      await vault.executeTransfer(high.requestId)
    ).wait();

    const after = await ethers.provider.getBalance(
      recipient.address
    );

    expect(after - before).to.equal(high.amount);

    const transfer = await vault.getTransfer(high.requestId);
    expect(transfer.amount).to.equal(0n);

    // 동일 거래 재실행 차단
    await expect(
      vault.executeTransfer(high.requestId)
    ).to.be.revertedWith("No ETH to transfer");
  });

  it("CRITICAL: 예치금이 환불되고 수신자 지급과 재실행이 차단된다", async function () {
    const {
      ethers,
      owner,
      sender,
      recipient,
      vault,
      result,
      domain,
    } = await setup();

    const critical = {
      ...result,
      riskScore: 90n,
      riskLevel: 3,
      requiresAuth: true,
      requiresAdminApproval: true,
      timelockUntil: 0n,
    };

    const signature = await owner.signTypedData(
      domain,
      types,
      critical
    );

    const senderBefore = await ethers.provider.getBalance(
      sender.address
    );
    const recipientBefore = await ethers.provider.getBalance(
      recipient.address
    );

    // 제출 가스비는 owner가 부담하므로 sender의 환불액을 직접 비교
    const ownerVault = vault.connect(owner) as Contract;

    await (
      await ownerVault.submitRiskResult(critical, signature)
    ).wait();

    const senderAfter = await ethers.provider.getBalance(
      sender.address
    );

    expect(senderAfter - senderBefore).to.equal(
      critical.amount
    );

    expect(
      await ethers.provider.getBalance(recipient.address)
    ).to.equal(recipientBefore);

    expect(
      await ethers.provider.getBalance(
        await vault.getAddress()
      )
    ).to.equal(0n);

    const transfer = await vault.getTransfer(
      critical.requestId
    );

    expect(transfer.riskLevel).to.equal(3n);
    expect(transfer.amount).to.equal(0n);

    await expect(
      vault.executeTransfer(critical.requestId)
    ).to.be.revertedWith("No ETH to transfer");

    await expect(
      vault.completeAuth(critical.requestId)
    ).to.be.revertedWith("Invalid status");

    await expect(
      vault.approveTransfer(critical.requestId)
    ).to.be.revertedWith("Not HIGH risk");
  });
});
