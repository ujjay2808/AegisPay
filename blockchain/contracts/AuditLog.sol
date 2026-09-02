// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract AuditLog {
  error RecordNotFound();

  enum Decision {
    Approved,
    Denied,
    Escalated
  }

  struct AuditRecord {
    bytes32 decisionHash;
    Decision decision;
    uint256 timestamp;
    address submittedBy;
  }

  mapping(uint256 => AuditRecord) private recordsById;
  mapping(bytes32 => uint256) private recordIdByHash;
  uint256 private nextRecordId = 1;

  event DecisionLogged(
    uint256 indexed recordId,
    bytes32 indexed decisionHash,
    Decision decision,
    uint256 timestamp,
    address submittedBy
  );

  function logDecision(bytes32 decisionHash, Decision decision) external returns (uint256 recordId) {
    recordId = nextRecordId++;
    AuditRecord memory record = AuditRecord({
      decisionHash: decisionHash,
      decision: decision,
      timestamp: block.timestamp,
      submittedBy: msg.sender
    });

    recordsById[recordId] = record;
    recordIdByHash[decisionHash] = recordId;

    emit DecisionLogged(recordId, decisionHash, decision, record.timestamp, record.submittedBy);
  }

  function getRecordByHash(bytes32 decisionHash) external view returns (AuditRecord memory) {
    uint256 recordId = recordIdByHash[decisionHash];
    if (recordId == 0) revert RecordNotFound();
    return recordsById[recordId];
  }

  function getRecordById(uint256 recordId) external view returns (AuditRecord memory) {
    if (recordId == 0 || recordId >= nextRecordId) revert RecordNotFound();
    return recordsById[recordId];
  }
}