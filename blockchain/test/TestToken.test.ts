
import { expect } from "chai";
import { network } from "hardhat";

describe("TestToken", function () {
  it("배포자에게 100만 개의 토큰을 발행한다", async function () {
    const { ethers } = await network.connect();
    const [owner] = await ethers.getSigners();

    const token = await ethers.deployContract("TestToken");

    expect(await token.name()).to.equal("AIconics Test Token");
    expect(await token.symbol()).to.equal("AIT");
    expect(await token.balanceOf(owner.address)).to.equal(
      ethers.parseUnits("1000000", 18)
    );
  });
});
