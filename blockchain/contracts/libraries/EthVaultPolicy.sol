
 // SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

library EthVaultPolicy {
    function validate(
        uint8 riskLevel,
        bool requiresAuth,
        bool requiresAdminApproval,
        uint256 timelockUntil
    ) internal view {
        require(riskLevel <= 3, "Invalid risk level");

        if (riskLevel == 0) {
            require(
                !requiresAuth && !requiresAdminApproval,
                "Invalid LOW policy"
            );
            require(timelockUntil == 0, "Invalid LOW timelock");
        } else if (riskLevel == 1) {
            require(
                requiresAuth && !requiresAdminApproval,
                "Invalid MEDIUM policy"
            );
            require(timelockUntil == 0, "Invalid MEDIUM timelock");
        } else if (riskLevel == 2) {
            require(
                requiresAuth && requiresAdminApproval,
                "Invalid HIGH policy"
            );
            require(
                timelockUntil >= block.timestamp,
                "Invalid HIGH timelock"
            );
        } else {
            require(
                requiresAuth && requiresAdminApproval,
                "Invalid CRITICAL policy"
            );
            require(timelockUntil == 0, "Invalid CRITICAL timelock");
        }
    }
}
