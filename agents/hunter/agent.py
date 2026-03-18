"""Hunter Agent: scans bounties, finds vulnerabilities, submits findings."""
import argparse
import os
import time

from common.contracts import get_web3, get_all_contracts
from common.config import load_deployments
from common.ipfs import download_json
from common.block_cursor import BlockCursor
from hunter.scanner import run_slither, parse_findings
from hunter.reasoning import analyze_findings
from hunter.poc_generator import generate_poc
from hunter.submitter import submit_finding

SEVERITY_MAP = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


def scan_bounty(w3, contracts, bounty_id: int, hunter_agent_id: int, executor_pubkey: bytes):
    """Scan a single bounty: fetch scope, analyze, submit findings."""
    bounty = contracts["bountyRegistry"].functions.getBounty(bounty_id).call()
    scope_uri = bounty[2]  # scopeURI
    print(f"Scanning bounty #{bounty_id}: {bounty[1]} (scope: {scope_uri})")

    # Fetch in-scope contract sources from IPFS
    scope_data = download_json(scope_uri.replace("ipfs://", ""))
    contract_sources = scope_data.get("contracts", {})

    for name, source in contract_sources.items():
        print(f"  Analyzing {name}...")

        # 1. Run Slither
        slither_output = run_slither(source, f"{name}.sol")
        findings = parse_findings(slither_output, min_impact="Medium")
        if not findings:
            print(f"  No significant findings in {name}")
            continue

        print(f"  Found {len(findings)} findings, running LLM analysis...")

        # 2. LLM reasoning
        analysis = analyze_findings(findings, source)
        exploitable = analysis.get("exploitable", [])
        if not exploitable:
            print(f"  No exploitable findings in {name}")
            continue

        # 3. Generate and submit PoCs for each exploitable finding
        for finding in exploitable:
            severity = SEVERITY_MAP.get(finding.get("severity", "LOW"), 1)
            print(f"  Generating PoC for {finding['finding']} (severity: {finding['severity']})")

            poc_source = generate_poc(
                finding=finding,
                contract_source=source,
                contract_address="0x0000000000000000000000000000000000000000",  # Will be filled by executor
            )

            report = {
                "contract": name,
                "finding": finding["finding"],
                "severity": finding["severity"],
                "strategy": finding.get("strategy", ""),
            }

            result = submit_finding(
                report=report,
                poc_source=poc_source,
                bounty_id=bounty_id,
                hunter_agent_id=hunter_agent_id,
                claimed_severity=severity,
                executor_pubkey=executor_pubkey,
            )
            print(f"  Submitted bug #{result['bug_id']}")


def main():
    parser = argparse.ArgumentParser(description="Hunter Agent")
    parser.add_argument("--bounty-id", type=int, help="Specific bounty to scan")
    parser.add_argument("--watch", action="store_true", help="Watch for new bounties")
    args = parser.parse_args()

    w3 = get_web3()
    contracts = get_all_contracts(w3)
    deployments = load_deployments()
    hunter_agent_id = deployments["agentIds"]["hunter"]

    # Fetch executor's ECIES public key from chain
    executor_agent_id = deployments["agentIds"]["executor"]
    executor_pubkey = contracts["identityRegistry"].functions.getMetadata(
        executor_agent_id, "eciesPubKey"
    ).call()

    if args.bounty_id:
        scan_bounty(w3, contracts, args.bounty_id, hunter_agent_id, executor_pubkey)
    elif args.watch:
        print("Watching for new bounties... (Ctrl+C to stop)")
        cursor = BlockCursor("hunter")
        seen_bounties = set()
        while True:
            latest = w3.eth.block_number
            last = cursor.get_last_block()
            if latest > last:
                count = contracts["bountyRegistry"].functions.getBountyCount().call()
                for i in range(1, count + 1):
                    if i not in seen_bounties:
                        seen_bounties.add(i)
                        scan_bounty(w3, contracts, i, hunter_agent_id, executor_pubkey)
                cursor.set_last_block(latest)
            time.sleep(10)


if __name__ == "__main__":
    main()
