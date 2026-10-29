
import { expect } from "chai";
import { network } from "hardhat";

describe("RiskTransfer", function () {
  async function setup() {
    const { ethers } = await network.connect();
    const [owner, sender, recipient, attacker] =
      await ethers.getSigners();

    const token = await ethers.deployContract("TestToken");
    const transfer = await ethers.deployContract("RiskTransfer", [
      await token.getAddress(),
      owner.address,
    ]);

    const amount = ethers.parseUnits("100", 18);

    await token.transfer(sender.address, amount);
    await token.connect(sender).approve(
      await transfer.getAddress(),
      amount
    );

    const block = await ethers.provider.getBlock("latest");

    const domain = {
      name: "AIconicsRiskTransfer",
      version: "1",
      chainId: (await ethers.provider.getNetwork()).chainId,
      verifyingContract: await transfer.getAddress(),
    };

    const types = {
      RiskTransfer: [
        { name: "sender", type: "address" },
        { name: "recipient", type: "address" },
        { name: "amount", type: "uint256" },
        { name: "riskScore", type: "uint256" },
        { name: "riskLevel", type: "uint8" },
        { name: "requestId", type: "bytes32" },
        { name: "deadline", type: "uint256" },
        { name: "nonce", type: "bytes32" },
      ],
    };

    const request = {
      sender: sender.address,
      recipient: recipient.address,
      amount,
      riskScore: 25,
      riskLevel: 0,
      requestId: ethers.id("request-1"),
      deadline: BigInt(block!.timestamp + 3600),
      nonce: ethers.id("nonce-1"),
    };

    const signature = await owner.signTypedData(
      domain,
      types,
      request
    );

    return {
      ethers, owner, sender, recipient, attacker,
      token, transfer, amount, domain, types,
      request, signature,
    };
  }

  it("LOW 거래는 송금에 성공한다", async function () {
    const { token, transfer, recipient, request, signature, amount } =
      await setup();

    await transfer.executeTransfer(request, signature);

    expect(await token.balanceOf(recipient.address)).to.equal(amount);
  });

  it("MEDIUM 거래는 차단한다", async function () {
    const { transfer, request, signature } = await setup();

    await expect(
      transfer.executeTransfer(
        { ...request, riskLevel: 1 },
        signature
      )
    ).to.be.rejectedWith("Risk level not LOW");
  });

  it("잘못된 서명은 차단한다", async function () {
    const { transfer, attacker, domain, types, request } =
      await setup();

    const invalidSignature = await attacker.signTypedData(
      domain, types, request
    );

    await expect(
      transfer.executeTransfer(request, invalidSignature)
    ).to.be.rejectedWith("Invalid signature");
  });

  it("동일한 요청의 중복 송금을 차단한다", async function () {
    const { transfer, request, signature } = await setup();

    await transfer.executeTransfer(request, signature);

    await expect(
      transfer.executeTransfer(request, signature)
    ).to.be.rejectedWith("Nonce already used");
  });

  it("HIGH와 CRITICAL 거래는 차단한다", async function () {
    const { transfer, request, signature } = await setup();

    for (const riskLevel of [2, 3]) {
      await expect(
        transfer.executeTransfer(
          { ...request, riskLevel },
          signature
        )
      ).to.be.rejectedWith("Risk level not LOW");
    }
  });

  it("만료된 거래는 차단한다", async function () {
    const { transfer, owner, domain, types, request } =
      await setup();

    const expiredRequest = {
      ...request,
      deadline: 1n,
    };

    const signature = await owner.signTypedData(
      domain,
      types,
      expiredRequest
    );

    await expect(
      transfer.executeTransfer(expiredRequest, signature)
    ).to.be.rejectedWith("Request expired");
  });
});