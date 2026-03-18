// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/mocks/MockUSDC.sol";
import "../src/erc8004/IdentityRegistry.sol";
import "../src/erc8004/ReputationRegistry.sol";
import "../src/erc8004/ValidationRegistry.sol";
import "../src/BountyRegistry.sol";
import "../src/BugSubmission.sol";
import "../src/ArbiterContract.sol";

contract Deploy is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        // Deploy registries
        MockUSDC usdc = new MockUSDC();
        IdentityRegistry identity = new IdentityRegistry();
        ReputationRegistry reputation = new ReputationRegistry();
        ValidationRegistry validation = new ValidationRegistry();

        // Deploy core contracts
        BountyRegistry bountyReg = new BountyRegistry(address(usdc), address(identity));
        BugSubmission bugSub = new BugSubmission(
            address(usdc), address(identity), address(reputation), address(bountyReg)
        );
        ArbiterContract arbiter = new ArbiterContract(
            address(identity), address(reputation), address(validation), address(bugSub)
        );

        // Wire up cross-references
        bountyReg.setBugSubmissionContract(address(bugSub));
        bugSub.setArbiterContract(address(arbiter));
        reputation.addAuthorizedCaller(address(arbiter));

        vm.stopBroadcast();

        console.log("MockUSDC:", address(usdc));
        console.log("IdentityRegistry:", address(identity));
        console.log("ReputationRegistry:", address(reputation));
        console.log("ValidationRegistry:", address(validation));
        console.log("BountyRegistry:", address(bountyReg));
        console.log("BugSubmission:", address(bugSub));
        console.log("ArbiterContract:", address(arbiter));
    }
}
