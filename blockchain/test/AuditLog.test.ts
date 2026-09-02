import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { network } from "hardhat";

describe("AuditLog", async function () {
  const { viem } = await network.create();
  const publicClient = await viem.getPublicClient();
  const [senderClient] = await viem.getWalletClients();

  it("logDecision() stores a record and returns recordId starting at 1", async function () {
    const auditLog = await viem.deployContract("AuditLog");
    const decisionHash = `0x${"11".repeat(32)}`;

    const { result: recordId } = await auditLog.simulate.logDecision([decisionHash, 0]);

    await auditLog.write.logDecision([decisionHash, 0]);

    const record = await auditLog.read.getRecordById([recordId]);

    assert.equal(recordId, 1n);
    assert.equal(record.decisionHash, decisionHash);
    assert.equal(record.decision, 0);
    assert.ok(record.timestamp > 0n);
    assert.equal(record.submittedBy.toLowerCase(), senderClient.account.address.toLowerCase());
  });

  it("logDecision() emits DecisionLogged with correct args", async function () {
    const auditLog = await viem.deployContract("AuditLog");
    const decisionHash = `0x${"22".repeat(32)}`;

    const txHash = await auditLog.write.logDecision([decisionHash, 1]);
    const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });
    const [event] = await publicClient.getContractEvents({
      address: auditLog.address,
      abi: auditLog.abi,
      eventName: "DecisionLogged",
      fromBlock: receipt.blockNumber,
      toBlock: receipt.blockNumber,
      strict: true,
    });
    const block = await publicClient.getBlock({ blockNumber: receipt.blockNumber });

    assert.equal(event.args.recordId, 1n);
    assert.equal(event.args.decisionHash, decisionHash);
    assert.equal(event.args.decision, 1);
    assert.equal(event.args.timestamp, block.timestamp);
    assert.equal(event.args.submittedBy.toLowerCase(), senderClient.account.address.toLowerCase());
  });

  it("getRecordByHash() returns the correct record after logging", async function () {
    const auditLog = await viem.deployContract("AuditLog");
    const decisionHash = `0x${"33".repeat(32)}`;

    await auditLog.write.logDecision([decisionHash, 2]);
    const record = await auditLog.read.getRecordByHash([decisionHash]);

    assert.equal(record.decisionHash, decisionHash);
    assert.equal(record.decision, 2);
    assert.ok(record.timestamp > 0n);
    assert.equal(record.submittedBy.toLowerCase(), senderClient.account.address.toLowerCase());
  });

  it("getRecordByHash() reverts with RecordNotFound() for a hash that was never logged", async function () {
    const auditLog = await viem.deployContract("AuditLog");
    const missingHash = `0x${"44".repeat(32)}`;

    await assert.rejects(auditLog.read.getRecordByHash([missingHash]), /RecordNotFound/);
  });

  it("getRecordById() returns the correct record after logging", async function () {
    const auditLog = await viem.deployContract("AuditLog");
    const decisionHash = `0x${"55".repeat(32)}`;

    const { result: recordId } = await auditLog.simulate.logDecision([decisionHash, 0]);
    await auditLog.write.logDecision([decisionHash, 0]);
    const record = await auditLog.read.getRecordById([recordId]);

    assert.equal(record.decisionHash, decisionHash);
    assert.equal(record.decision, 0);
    assert.ok(record.timestamp > 0n);
    assert.equal(record.submittedBy.toLowerCase(), senderClient.account.address.toLowerCase());
  });

  it("getRecordById() reverts with RecordNotFound() for id 0 and for an id beyond what's been logged", async function () {
    const auditLog = await viem.deployContract("AuditLog");
    const decisionHash = `0x${"66".repeat(32)}`;

    await auditLog.write.logDecision([decisionHash, 1]);

    await assert.rejects(auditLog.read.getRecordById([0n]), /RecordNotFound/);
    await assert.rejects(auditLog.read.getRecordById([2n]), /RecordNotFound/);
  });

  it("logging two different decisions produces two different recordIds", async function () {
    const auditLog = await viem.deployContract("AuditLog");
    const firstHash = `0x${"77".repeat(32)}`;
    const secondHash = `0x${"88".repeat(32)}`;

    const { result: firstRecordId } = await auditLog.simulate.logDecision([firstHash, 0]);
    await auditLog.write.logDecision([firstHash, 0]);
    const { result: secondRecordId } = await auditLog.simulate.logDecision([secondHash, 2]);
    await auditLog.write.logDecision([secondHash, 2]);

    assert.equal(firstRecordId, 1n);
    assert.equal(secondRecordId, 2n);
  });
});