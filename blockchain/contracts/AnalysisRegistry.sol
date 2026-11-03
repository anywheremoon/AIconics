// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice 위험 분석 결과의 해시를 기록하고 조회한다.
contract AnalysisRegistry {
    address public immutable owner;

    struct AnalysisRecord {
        uint256 transactionId;
        bytes32 digest;
        uint256 recordedAt;
        bool exists;
    }

    mapping(uint256 => AnalysisRecord) private records;

    event AnalysisRecorded(
        uint256 indexed analysisId,
        uint256 indexed transactionId,
        bytes32 digest,
        uint256 recordedAt
    );

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Unauthorized");
        _;
    }

    /// @notice 같은 분석 ID의 기록은 덮어쓸 수 없다.
    function recordAnalysis(
        uint256 analysisId,
        uint256 transactionId,
        bytes32 digest
    ) external onlyOwner {
        require(analysisId > 0, "Invalid analysis ID");
        require(transactionId > 0, "Invalid transaction ID");
        require(digest != bytes32(0), "Invalid digest");
        require(!records[analysisId].exists, "Already recorded");

        records[analysisId] = AnalysisRecord({
            transactionId: transactionId,
            digest: digest,
            recordedAt: block.timestamp,
            exists: true
        });

        emit AnalysisRecorded(
            analysisId,
            transactionId,
            digest,
            block.timestamp
        );
    }

    /// @notice 미기록 분석은 exists=false로 반환한다.
    function getAnalysis(
        uint256 analysisId
    )
        external
        view
        returns (
            bool exists,
            uint256 transactionId,
            bytes32 digest,
            uint256 recordedAt
        )
    {
        AnalysisRecord storage record = records[analysisId];

        return (
            record.exists,
            record.transactionId,
            record.digest,
            record.recordedAt
        );
    }
}
