
import { ethers } from "ethers";
import fs from "node:fs";

const provider = new ethers.JsonRpcProvider("http://127.0.0.1:8545");

const deployment = JSON.parse(
  fs.readFileSync("./deployments/eth-risk-vault.localhost.json", "utf8")
);

const abi = JSON.parse(
  fs.readFileSync("./deployments/EthRiskVault.abi.json", "utf8")
);

const network = await provider.getNetwork();

if (network.chainId.toString() !== deployment.chainId) {
  throw new Error("Chain ID mismatch");
}

const code = await provider.getCode(deployment.contractAddress);

if (code === "0x") {
  throw new Error("Contract not found at deployment address");
}

const vault = new ethers.Contract(
  deployment.contractAddress,
  abi,
  provider
);

const riskSigner = await vault.riskSigner();
const authOperator = await vault.authOperator();

if (riskSigner.toLowerCase() !== deployment.riskSigner.toLowerCase()) {
  throw new Error("Risk signer mismatch");
}

if (authOperator.toLowerCase() !== deployment.authOperator.toLowerCase()) {
  throw new Error("Auth operator mismatch");
}

console.log("EthRiskVault verification passed");
console.log("Contract:", deployment.contractAddress);
console.log("Chain ID:", network.chainId.toString());
console.log("Risk signer:", riskSigner);
console.log("Auth operator:", authOperator);
