
 // SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

contract RiskTransfer is EIP712 {
    IERC20 public immutable token;
    address public authorizedSigner;

    mapping(bytes32 => bool) public usedNonces;
    mapping(bytes32 => bool) public usedRequestIds;

    bytes32 private constant TRANSFER_TYPEHASH = keccak256(
        "RiskTransfer(address sender,address recipient,uint256 amount,uint256 riskScore,uint8 riskLevel,bytes32 requestId,uint256 deadline,bytes32 nonce)"
    );

    struct TransferRequest {
        address sender;
        address recipient;
        uint256 amount;
        uint256 riskScore;
        uint8 riskLevel;
        bytes32 requestId;
        uint256 deadline;
        bytes32 nonce;
    }

    event TransferExecuted(
        bytes32 indexed requestId,
        address indexed sender,
        address indexed recipient,
        uint256 amount
    );

    constructor(address tokenAddress, address signer)
        EIP712("AIconicsRiskTransfer", "1")
    {
        require(tokenAddress != address(0), "Invalid token");
        require(signer != address(0), "Invalid signer");

        token = IERC20(tokenAddress);
        authorizedSigner = signer;
    }

    function executeTransfer(
        TransferRequest calldata request,
        bytes calldata signature
    ) external {
        require(request.riskLevel == 0, "Risk level not LOW");
        require(request.riskScore <= 100, "Invalid risk score");
        require(request.sender != address(0), "Invalid sender");
        require(request.recipient != address(0), "Invalid recipient");
        require(request.amount > 0, "Invalid amount");
        require(block.timestamp <= request.deadline, "Request expired");
        require(!usedNonces[request.nonce], "Nonce already used");
        require(!usedRequestIds[request.requestId], "Request already used");

        bytes32 structHash = keccak256(
            abi.encode(
                TRANSFER_TYPEHASH,
                request.sender,
                request.recipient,
                request.amount,
                request.riskScore,
                request.riskLevel,
                request.requestId,
                request.deadline,
                request.nonce
            )
        );

        bytes32 digest = _hashTypedDataV4(structHash);
        address recoveredSigner = ECDSA.recover(digest, signature);

        require(recoveredSigner == authorizedSigner, "Invalid signature");

        usedNonces[request.nonce] = true;
        usedRequestIds[request.requestId] = true;

        require(
            token.transferFrom(
                request.sender,
                request.recipient,
                request.amount
            ),
            "Transfer failed"
        );

        emit TransferExecuted(
            request.requestId,
            request.sender,
            request.recipient,
            request.amount
        );
    }
}
