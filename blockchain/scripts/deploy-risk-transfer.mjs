
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { JsonRpcProvider, ContractFactory } from "ethers";

const provider = new JsonRpcProvider("http://127.0.0.1:8545");

async function deploy(name, signer, args = []) {
  const artifact = JSON.parse(
    await readFile(
      new URL(`../artifacts/contracts/${name}.sol/${name}.json`, import.meta.url),
      "utf8"
    )
  );

  const factory = new ContractFactory(
    artifact.abi,
    artifact.bytecode,
    signer
  );

  const contract = await factory.deploy(...args);
  await contract.waitForDeployment();

  return { contract, abi: artifact.abi };
}

try {
  const network = await provider.getNetwork();

  if (network.chainId !== 31337n) {
    throw new Error("Expected local chain ID 31337");
  }

  const signer = await provider.getSigner(0);
  const signerAddress = await signer.getAddress();

  const token = await deploy("TestToken", signer);

  const riskTransfer = await deploy("RiskTransfer", signer, [
    await token.contract.getAddress(),
    signerAddress,
  ]);

  const result = {
    chainId: Number(network.chainId),
    tokenAddress: await token.contract.getAddress(),
    riskTransferAddress: await riskTransfer.contract.getAddress(),
    authorizedSigner: signerAddress,
  };

  const outputDir = new URL("../deployments/", import.meta.url);
  await mkdir(outputDir, { recursive: true });

  await writeFile(
    new URL("risk-transfer-localhost.json", outputDir),
    JSON.stringify(result, null, 2),
    "utf8"
  );

  await writeFile(
    new URL("RiskTransfer.abi.json", outputDir),
    JSON.stringify(riskTransfer.abi, null, 2),
    "utf8"
  );

  await writeFile(
    new URL("TestToken.abi.json", outputDir),
    JSON.stringify(token.abi, null, 2),
    "utf8"
  );

  console.log("DEPLOY_SUCCESS");
  console.log(result);
} catch (error) {
  console.error("DEPLOY_FAILED:", error);
  process.exitCode = 1;
} finally {
  provider.destroy();
}
