
 // SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "./libraries/EthVaultTypes.sol";
import "./libraries/EthVaultPolicy.sol";

contract EthRiskVault is Ownable, ReentrancyGuard, EIP712 {


    // EthVaultTypes 라이브러리의 자료형 사용
    // 모든 기존 함수에서 타입 이름을 변경해야 함

    uint256 public nextRequestId;

    address public riskSigner;
    address public authOperator;
    mapping(bytes32 => bool) public usedNonces;


    mapping(bytes32 => EthVaultTypes.TransferRequest) private transfers;


bytes32 private constant RISK_RESULT_TYPEHASH = keccak256(
    "RiskResult(bytes32 requestId,address sender,address recipient,uint256 amount,uint256 riskScore,uint8 riskLevel,bool requiresAuth,bool requiresAdminApproval,uint256 timelockUntil,uint256 deadline,bytes32 analysisHash,bytes32 nonce)"
);

function _verifyRiskSignature(
    EthVaultTypes.RiskResult calldata result,
    bytes calldata signature
) internal view returns (bool) {
    bytes32 structHash = keccak256(
        abi.encode(
            RISK_RESULT_TYPEHASH,
            result.requestId,
            result.sender,
            result.recipient,
            result.amount,
            result.riskScore,
            result.riskLevel,
            result.requiresAuth,
            result.requiresAdminApproval,
            result.timelockUntil,
            result.deadline,
            result.analysisHash,
            result.nonce
        )
    );

    bytes32 digest = _hashTypedDataV4(structHash);

    address recoveredSigner = ECDSA.recover(digest, signature);

    return recoveredSigner == riskSigner;
}


    constructor(address _riskSigner, address _authOperator)
        Ownable(msg.sender)
        EIP712("AIconics EthRiskVault", "1")
    {
        require(_riskSigner != address(0), "Invalid risk signer");
        require(_authOperator != address(0), "Invalid auth operator");

        riskSigner = _riskSigner;
        authOperator = _authOperator;
    }



event TransferRequested(
    bytes32 indexed requestId,
    address indexed sender,
    address indexed recipient,
    uint256 amount
);

function requestTransfer(
    address payable recipient
) external payable nonReentrant returns (bytes32) {
    require(msg.value > 0, "Amount must be greater than zero");
    require(recipient != address(0), "Invalid recipient");

    bytes32 requestId = bytes32(nextRequestId);
    nextRequestId++;



    EthVaultTypes.TransferRequest storage newTransfer = transfers[requestId];

    newTransfer.sender = msg.sender;
    newTransfer.recipient = recipient;
    newTransfer.amount = msg.value;
    newTransfer.riskLevel = EthVaultTypes.RiskLevel.LOW;
    newTransfer.status = EthVaultTypes.TransferStatus.REQUESTED;
    newTransfer.createdAt = block.timestamp;



    emit TransferRequested(
        requestId,
        msg.sender,
        recipient,
        msg.value
    );

    return requestId;
}

event RiskResultSubmitted(
    bytes32 indexed requestId,
    EthVaultTypes.RiskLevel riskLevel
);

function submitRiskResult(
    EthVaultTypes.RiskResult calldata result,
    bytes calldata signature
) external nonReentrant {
    EthVaultTypes.TransferRequest storage transfer = transfers[result.requestId];

    require(transfer.sender != address(0), "Request not found");
    require(transfer.status == EthVaultTypes.TransferStatus.REQUESTED, "Invalid status");

    require(block.timestamp <= result.deadline, "Signature expired");
    require(!usedNonces[result.nonce], "Nonce already used");

    require(transfer.sender == result.sender, "Sender mismatch");
    require(transfer.recipient == result.recipient, "Recipient mismatch");
    require(transfer.amount == result.amount, "Amount mismatch");

    require(result.riskLevel <= uint8(EthVaultTypes.RiskLevel.CRITICAL), "Invalid risk level");
    require(_verifyRiskSignature(result, signature), "Invalid signature");

    // A 獄쏄퉮肉??뽰벥 ?袁る퓮 ?源껎닋癰??類ㅼ퐠 ?類ㅼ뵥
    EthVaultPolicy.validate(
    result.riskLevel,
    result.requiresAuth,
    result.requiresAdminApproval,
    result.timelockUntil
    );

    usedNonces[result.nonce] = true;

    transfer.riskScore = result.riskScore;
    transfer.riskLevel = EthVaultTypes.RiskLevel(result.riskLevel);
    transfer.requiresAuth = result.requiresAuth;
    transfer.requiresAdminApproval = result.requiresAdminApproval;
    transfer.timelockUntil = result.timelockUntil;
    transfer.deadline = result.deadline;
    transfer.analysisHash = result.analysisHash;

    if (result.riskLevel == uint8(EthVaultTypes.RiskLevel.CRITICAL)) {
        transfer.status = EthVaultTypes.TransferStatus.REJECTED;

        uint256 refundAmount = transfer.amount;
        transfer.amount = 0;

        (bool success, ) = payable(transfer.sender).call{value: refundAmount}("");
        require(success, "Refund failed");
    } else {
        transfer.status = EthVaultTypes.TransferStatus.ANALYZED;
    }

    emit RiskResultSubmitted(result.requestId, transfer.riskLevel);
}

event AuthCompleted(bytes32 indexed requestId);

function completeAuth(bytes32 requestId) external {
    require(msg.sender == authOperator, "Not authorized");

    EthVaultTypes.TransferRequest storage transfer = transfers[requestId];

    require(transfer.sender != address(0), "Request not found");
    require(transfer.status == EthVaultTypes.TransferStatus.ANALYZED, "Invalid status");
    require(transfer.requiresAuth, "Auth not required");
    require(!transfer.authCompleted, "Auth already completed");

    transfer.authCompleted = true;
    transfer.status = EthVaultTypes.TransferStatus.AUTHENTICATED;

    emit AuthCompleted(requestId);
}

event TransferApproved(bytes32 indexed requestId);

function approveTransfer(bytes32 requestId) external onlyOwner {
    EthVaultTypes.TransferRequest storage transfer = transfers[requestId];

    require(transfer.sender != address(0), "Request not found");
    require(transfer.riskLevel == EthVaultTypes.RiskLevel.HIGH, "Not HIGH risk");
    require(transfer.status == EthVaultTypes.TransferStatus.AUTHENTICATED, "Invalid status");
    require(transfer.requiresAdminApproval, "Approval not required");
    require(transfer.authCompleted, "Auth not completed");
    require(!transfer.adminApproved, "Already approved");

    transfer.adminApproved = true;
    transfer.status = EthVaultTypes.TransferStatus.APPROVED;

    emit TransferApproved(requestId);
}

event TransferExecuted(
    bytes32 indexed requestId,
    address indexed recipient,
    uint256 amount
);

function executeTransfer(bytes32 requestId) external nonReentrant {
    EthVaultTypes.TransferRequest storage transfer = transfers[requestId];

    require(transfer.sender != address(0), "Request not found");
    require(transfer.amount > 0, "No ETH to transfer");
    require(
    block.timestamp < transfer.createdAt + REQUEST_EXPIRY,
    "Request expired"
    );

    require(
        transfer.status == EthVaultTypes.TransferStatus.ANALYZED ||
        transfer.status == EthVaultTypes.TransferStatus.AUTHENTICATED ||
        transfer.status == EthVaultTypes.TransferStatus.APPROVED,
        "Invalid status"
    );

    require(transfer.riskLevel != EthVaultTypes.RiskLevel.CRITICAL, "Critical risk");

    if (transfer.requiresAuth) {
        require(transfer.authCompleted, "Auth required");
    }

    if (transfer.requiresAdminApproval) {
        require(transfer.adminApproved, "Admin approval required");
    }

    require(
        block.timestamp >= transfer.timelockUntil,
        "Timelock active"
    );

    uint256 amount = transfer.amount;
    address payable recipient = transfer.recipient;

    // ??뷀닊 ?袁⑸퓠 ?怨밴묶 癰궰野?
    transfer.status = EthVaultTypes.TransferStatus.EXECUTED;
    transfer.amount = 0;

    (bool success, ) = recipient.call{value: amount}("");
    require(success, "ETH transfer failed");

    emit TransferExecuted(requestId, recipient, amount);
}

event TransferRejected(
    bytes32 indexed requestId,
    uint256 refundedAmount
);

function rejectTransfer(bytes32 requestId)
    external
    onlyOwner
    nonReentrant
{
    EthVaultTypes.TransferRequest storage transfer = transfers[requestId];

    require(transfer.sender != address(0), "Request not found");
    require(transfer.amount > 0, "No ETH to refund");

    require(
        transfer.status == EthVaultTypes.TransferStatus.REQUESTED ||
        transfer.status == EthVaultTypes.TransferStatus.ANALYZED ||
        transfer.status == EthVaultTypes.TransferStatus.AUTHENTICATED ||
        transfer.status == EthVaultTypes.TransferStatus.APPROVED,
        "Invalid status"
    );

    uint256 refundAmount = transfer.amount;
    address payable sender = payable(transfer.sender);

    // ??롰뀑 ?袁⑸퓠 ?怨밴묶?? ?遺용만 癰궰野?
    transfer.status = EthVaultTypes.TransferStatus.REJECTED;
    transfer.amount = 0;

    (bool success, ) = sender.call{value: refundAmount}("");
    require(success, "Refund failed");

    emit TransferRejected(requestId, refundAmount);
}

uint256 public constant REQUEST_EXPIRY = 24 hours;

event TransferCancelled(
    bytes32 indexed requestId,
    uint256 refundedAmount
);

function cancelExpired(bytes32 requestId)
    external
    nonReentrant
{
    EthVaultTypes.TransferRequest storage transfer = transfers[requestId];

    require(transfer.sender != address(0), "Request not found");
    require(msg.sender == transfer.sender, "Not sender");
    require(transfer.amount > 0, "No ETH to refund");

    require(
        transfer.status != EthVaultTypes.TransferStatus.EXECUTED &&
        transfer.status != EthVaultTypes.TransferStatus.REJECTED &&
        transfer.status != EthVaultTypes.TransferStatus.CANCELLED,
        "Already finalized"
    );

    require(
        block.timestamp >= transfer.createdAt + REQUEST_EXPIRY,
        "Request not expired"
    );

    uint256 refundAmount = transfer.amount;

    transfer.status = EthVaultTypes.TransferStatus.CANCELLED;
    transfer.amount = 0;

    (bool success, ) = payable(transfer.sender).call{value: refundAmount}("");
    require(success, "Refund failed");

    emit TransferCancelled(requestId, refundAmount);
}

}
