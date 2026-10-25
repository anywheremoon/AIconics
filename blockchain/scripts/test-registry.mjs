import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  JsonRpcProvider,
  Contract,
  sha256,
  toUtf8Bytes,
  randomBytes,
  hexlify,
} from "ethers";

const provider = new JsonRpcProvider("http://127.0.0.1:8545");

async function expectRevert(label, action) {
  let rejected = false;

  try {
    const tx = await action();
    await tx.wait();
  } catch (error) {
    if (error.code !== "CALL_EXCEPTION") {
      throw error;
    }
    rejected = true;
  }

  assert.equal(rejected, true, `${label}: transaction was not rejected`);
  console.log(`${label}: PASS`);
}

try {
  const deployment = JSON.parse(
    await readFile(
      new URL("../deployments/localhost.json", import.meta.url),
      "utf8"
    )
  );

  const abi = JSON.parse(
    await readFile(
      new URL("../deployments/AnalysisRegistry.abi.json", import.meta.url),
      "utf8"
    )
  );

  const network = await provider.getNetwork();
  assert.equal(network.chainId, 31337n);

  const code = await provider.getCode(deployment.contract_address);
  assert.notEqual(code, "0x", "Contract not found. Redeploy first.");

  const ownerSigner = await provider.getSigner(0);
  const otherSigner = await provider.getSigner(1);

  const contract = new Contract(
    deployment.contract_address,
    abi,
    ownerSigner
  );

  assert.equal(
    (await contract.owner()).toLowerCase(),
    (await ownerSigner.getAddress()).toLowerCase()
  );

  // 実DBのIDとは無関係な、テスト専用のランダムID
  const analysisId = BigInt(hexlify(randomBytes(16)));
  const transactionId = 999999n;

  // テスト用データ。Bの正式な直列化ルールとは別。
  const originalData = JSON.stringify({
    transaction_id: transactionId.toString(),
    final_risk_score: "80.75",
    risk_level: "HIGH",
  });

  const originalHash = sha256(toUtf8Bytes(originalData));

  const before = await contract.getAnalysis(analysisId);
  assert.equal(before.exists, false);
  console.log("NOT_RECORDED: PASS");

  const tx = await contract.recordAnalysis(
    analysisId,
    transactionId,
    originalHash
  );

  const receipt = await tx.wait();
  assert.equal(receipt.status, 1);
  console.log("RECORD_HASH: PASS");

  const recorded = await contract.getAnalysis(analysisId);

  assert.equal(recorded.exists, true);
  assert.equal(recorded.transactionId, transactionId);
  assert.equal(recorded.digest, originalHash);
  assert.ok(recorded.recordedAt > 0n);
  console.log("READ_AND_MATCH: PASS");

  const changedData = JSON.stringify({
    transaction_id: transactionId.toString(),
    final_risk_score: "10.00",
    risk_level: "HIGH",
  });

  const changedHash = sha256(toUtf8Bytes(changedData));
  assert.notEqual(recorded.digest, changedHash);
  console.log("CHANGED_DATA_DETECTED: PASS");

  await expectRevert("DUPLICATE_BLOCKED", () =>
    contract.recordAnalysis(
      analysisId,
      transactionId,
      changedHash
    )
  );

  const unauthorizedContract = contract.connect(otherSigner);

  await expectRevert("UNAUTHORIZED_BLOCKED", () =>
    unauthorizedContract.recordAnalysis(
      analysisId + 1n,
      transactionId,
      originalHash
    )
  );

  const after = await contract.getAnalysis(analysisId);
  assert.equal(after.digest, originalHash);
  console.log("ORIGINAL_HASH_PRESERVED: PASS");

  console.log("ALL_TESTS_PASSED");
} catch (error) {
  console.error("TEST_FAILED:", error);
  process.exitCode = 1;
} finally {
  provider.destroy();
}