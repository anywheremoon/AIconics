import { readFile, mkdir, writeFile } from "node:fs/promises";
import { JsonRpcProvider, ContractFactory } from "ethers";

const rpcUrl = "http://127.0.0.1:8545";
const provider = new JsonRpcProvider(rpcUrl);

try {
  const artifactUrl = new URL(
    "../artifacts/contracts/AnalysisRegistry.sol/AnalysisRegistry.json",
    import.meta.url
  );

  const artifact = JSON.parse(
    await readFile(artifactUrl, "utf8")
  );

  const network = await provider.getNetwork();

  if (network.chainId !== 31337n) {
    throw new Error("Expected local development chain ID 31337");
  }

  // 로컬 노드가 제공하는 첫 번째 테스트 계정 사용
  const signer = await provider.getSigner(0);
  const deployer = await signer.getAddress();

  const factory = new ContractFactory(
    artifact.abi,
    artifact.bytecode,
    signer
  );

  const contract = await factory.deploy();
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  const owner = await contract.owner();

  if (owner.toLowerCase() !== deployer.toLowerCase()) {
    throw new Error("Owner verification failed");
  }

  const deployment = {
    rpc_url: rpcUrl,
    chain_id: Number(network.chainId),
    contract_address: address,
    owner_address: owner,
    deployment_tx_hash: contract.deploymentTransaction().hash,
  };

  const outputDir = new URL("../deployments/", import.meta.url);
  await mkdir(outputDir, { recursive: true });

  await writeFile(
    new URL("localhost.json", outputDir),
    JSON.stringify(deployment, null, 2),
    "utf8"
  );

  await writeFile(
    new URL("AnalysisRegistry.abi.json", outputDir),
    JSON.stringify(artifact.abi, null, 2),
    "utf8"
  );

  console.log("DEPLOY_SUCCESS");
  console.log(JSON.stringify(deployment, null, 2));
  console.log("OWNER_CHECK: PASS");
} catch (error) {
  console.error("DEPLOY_FAILED:", error);
  process.exitCode = 1;
} finally {
  provider.destroy();
}