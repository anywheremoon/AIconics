
 // SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

library EthVaultTypes {
    enum RiskLevel {
        LOW,
        MEDIUM,
        HIGH,
        CRITICAL
    }

    enum TransferStatus {
        REQUESTED,
        ANALYZED,
        AUTHENTICATED,
        APPROVED,
        EXECUTED,
        REJECTED,
        CANCELLED
    }

    struct TransferRequest {
        address sender;
        address payable recipient;
        uint256 amount;
        RiskLevel riskLevel;
        TransferStatus status;
        uint256 createdAt;
        uint256 riskScore;
        bool requiresAuth;
        bool requiresAdminApproval;
        bool authCompleted;
        bool adminApproved;
        uint256 timelockUntil;
        uint256 deadline;
        bytes32 analysisHash;
    }

    struct RiskResult {
        bytes32 requestId;
        address sender;
        address recipient;
        uint256 amount;
        uint256 riskScore;
        uint8 riskLevel;
        bool requiresAuth;
        bool requiresAdminApproval;
        uint256 timelockUntil;
        uint256 deadline;
        bytes32 analysisHash;
        bytes32 nonce;
    }
}
