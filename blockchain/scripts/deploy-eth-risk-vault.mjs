
import { ethers } from "ethers";
import fs from "node:fs";

const RPC_URL = "http://127.0.0.1:8545";

const provider = new ethers.JsonRpcProvider(RPC_URL);
const deployer = await provider.getSigner(0);

const artifact = JSON.parse(
  fs.readFileSync(
    "./artifacts/contracts/EthRiskVault.sol/EthRiskVault.json",
    "utf8"
  )
);

const factory = new ethers.ContractFactory(
  artifact.abi,
  artifact.bytecode,
  deployer
);

// 로컬 테스트에서는 배포자가 서명자와 인증 담당자를 겸함
const deployerAddress = await deployer.getAddress();

const vault = await factory.deploy(
  deployerAddress,
  deployerAddress
);

await vault.waitForDeployment();

const network = await provider.getNetwork();
const contractAddress = await vault.getAddress();

console.log("EthRiskVault deployed:", contractAddress);
console.log("Chain ID:", network.chainId.toString());
console.log("Risk signer:", deployerAddress);
console.log("Auth operator:", deployerAddress);

fs.mkdirSync("./deployments", { recursive: true });

// 1. 프론트엔드/백엔드 연동용 ABI
fs.writeFileSync(
  "./deployments/EthRiskVault.abi.json",
  JSON.stringify(artifact.abi, null, 2)
);

// 2. 로컬 배포 정보
fs.writeFileSync(
  "./deployments/eth-risk-vault.localhost.json",
  JSON.stringify(
    {
      chainId: network.chainId.toString(),
      contractAddress,
      riskSigner: deployerAddress,
      authOperator: deployerAddress
    },
    null,
    2
  )
);

console.log("ABI saved: deployments/EthRiskVault.abi.json");
console.log("Deployment saved: deployments/eth-risk-vault.localhost.json");
