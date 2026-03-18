// contracts/test/FullLifecycle.t.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/ArbiterContract.sol";
import "../src/BugSubmission.sol";
import "../src/BountyRegistry.sol";
import "../src/mocks/MockUSDC.sol";
import "../src/erc8004/IdentityRegistry.sol";
import "../src/erc8004/ReputationRegistry.sol";
import "../src/erc8004/ValidationRegistry.sol";

contract FullLifecycleTest is Test {
    // Full system test: bounty -> submit -> execute -> arbitrate -> payout -> reputation

    MockUSDC usdc;
    IdentityRegistry identity;
    ReputationRegistry reputation;
    ValidationRegistry validation;
    BountyRegistry bountyReg;
    BugSubmission bugSub;
    ArbiterContract arbiter;

    address owner = makeAddr("owner");
    address protocolOwner = makeAddr("protocol");
    address hunterOwner = makeAddr("hunter");
    address executorAddr = makeAddr("executor");
    address arb1 = makeAddr("arb1");
    address arb2 = makeAddr("arb2");
    address arb3 = makeAddr("arb3");

    function setUp() public {
        vm.startPrank(owner);
        usdc = new MockUSDC();
        identity = new IdentityRegistry();
        reputation = new ReputationRegistry();
        validation = new ValidationRegistry();
        bountyReg = new BountyRegistry(address(usdc), address(identity));
        bugSub = new BugSubmission(address(usdc), address(identity), address(reputation), address(bountyReg));
        arbiter = new ArbiterContract(address(identity), address(reputation), address(validation), address(bugSub));

        bountyReg.setBugSubmissionContract(address(bugSub));
        bugSub.setArbiterContract(address(arbiter));
        reputation.addAuthorizedCaller(address(arbiter));
        validation.addAuthorizedCaller(executorAddr);
        arbiter.setExecutor(executorAddr);

        // Mint agent IDs: protocol=1, hunter=2, executor=3, arb1=4, arb2=5, arb3=6
        identity.mintAgent(protocolOwner, "ipfs://protocol"); // ID 1
        identity.mintAgent(hunterOwner, "ipfs://hunter");     // ID 2
        identity.mintAgent(executorAddr, "ipfs://executor");   // ID 3
        identity.mintAgent(arb1, "ipfs://arb1");              // ID 4
        identity.mintAgent(arb2, "ipfs://arb2");              // ID 5
        identity.mintAgent(arb3, "ipfs://arb3");              // ID 6
        vm.stopPrank();

        // Register arbiters in pool
        vm.prank(arb1); arbiter.registerArbiter(4);
        vm.prank(arb2); arbiter.registerArbiter(5);
        vm.prank(arb3); arbiter.registerArbiter(6);

        // Fund wallets
        usdc.mint(protocolOwner, 50_000e6);
        usdc.mint(hunterOwner, 1_000e6);

        vm.prank(protocolOwner); usdc.approve(address(bountyReg), type(uint256).max);
        vm.prank(hunterOwner); usdc.approve(address(bugSub), type(uint256).max);
    }

    function test_full_lifecycle() public {
        // 1. Create bounty (50k USDC)
        vm.prank(protocolOwner);
        uint256 bountyId = bountyReg.createBounty(
            1, "TestProtocol", "ipfs://scope",
            BountyRegistry.Tiers(25_000e6, 10_000e6, 2_000e6, 500e6),
            50_000e6, block.timestamp + 30 days, 0
        );

        // 2. Hunter commits bug (CRITICAL claim, severity=4, hunterAgentId=2)
        //    Stake for unknown hunter at CRITICAL = 250e6
        string memory cid = "ipfs://encrypted";
        bytes32 salt = bytes32("huntersalt");
        bytes32 commitHash = keccak256(abi.encode(cid, uint256(2), salt));
        vm.prank(hunterOwner);
        uint256 bugId = bugSub.commitBug(bountyId, commitHash, 2, 4);

        // Hunter staked 250e6, balance = 1000 - 250 = 750e6
        assertEq(usdc.balanceOf(hunterOwner), 750e6);

        // 3. Hunter reveals
        vm.prank(hunterOwner);
        bugSub.revealBug(bugId, cid, salt);

        // 4. Executor registers state impact
        bytes32 reqHash = keccak256("statehash");
        vm.prank(executorAddr);
        validation.submitValidation(3, reqHash, "ipfs://statediff");
        vm.prank(executorAddr);
        arbiter.registerStateImpact(bugId, reqHash, "ipfs://statediff");

        // 5. Three arbiters commit votes
        //    arb1=CRITICAL(4), arb2=CRITICAL(4), arb3=HIGH(3)
        bytes32 s1 = bytes32("s1");
        bytes32 s2 = bytes32("s2");
        bytes32 s3 = bytes32("s3");
        vm.prank(arb1); arbiter.commitVote(bugId, keccak256(abi.encode(uint8(4), s1)));
        vm.prank(arb2); arbiter.commitVote(bugId, keccak256(abi.encode(uint8(4), s2)));
        vm.prank(arb3); arbiter.commitVote(bugId, keccak256(abi.encode(uint8(3), s3)));

        // 6. Three arbiters reveal votes
        vm.prank(arb1); arbiter.revealVote(bugId, 4, s1);
        vm.prank(arb2); arbiter.revealVote(bugId, 4, s2);
        vm.prank(arb3); arbiter.revealVote(bugId, 3, s3);

        // 7. Resolution: median([4,4,3]) = 4 (CRITICAL)
        //    Hunter gets 25,000e6 (CRITICAL payout) + 250e6 (stake returned)
        //    Hunter balance: 750 + 250 + 25000 = 26000e6
        assertEq(usdc.balanceOf(hunterOwner), 26_000e6);

        // 8. Verify submission state
        BugSubmission.Submission memory sub = bugSub.getSubmission(bugId);
        assertEq(sub.finalSeverity, 4);
        assertTrue(sub.isValid);

        // 9. Verify reputation feedback
        //    Hunter: +100 for valid CRITICAL submission
        assertEq(reputation.getReputation(2), 100);
        assertEq(reputation.getFeedbackCount(2, "submission_valid"), 1);

        //    Arb1 (agentId=4) and Arb2 (agentId=5) aligned with median(4): +10 each
        //    Arb3 (agentId=6) deviated from median: -5
        assertEq(reputation.getReputation(4), 10);
        assertEq(reputation.getReputation(5), 10);
        assertEq(reputation.getReputation(6), -5);

        // 10. Verify bounty remaining funds: 50k - 25k paid = 25k
        assertEq(bountyReg.getRemainingFunds(bountyId), 25_000e6);
    }
}
