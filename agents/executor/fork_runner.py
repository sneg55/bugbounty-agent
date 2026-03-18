# agents/executor/fork_runner.py
"""Runs hunter PoC scripts in a Foundry fork."""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from common.config import RPC_URL

# Resolve the contracts directory relative to this file:
# agents/executor/fork_runner.py -> agents/ -> project root -> contracts/
_CONTRACTS_DIR = Path(__file__).parent.parent.parent / "contracts"


def run_poc_in_fork(poc_source: str, fork_block: int | None = None) -> dict:
    """Execute a Foundry PoC test in a forked environment."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create minimal Foundry project structure
        src_dir = tmppath / "src"
        test_dir = tmppath / "test"
        src_dir.mkdir()
        test_dir.mkdir()

        (test_dir / "Exploit.t.sol").write_text(poc_source)

        # Copy foundry.toml and remappings.txt from the main contracts directory
        # so library paths and compiler settings are consistent.
        for config_file in ("foundry.toml", "remappings.txt"):
            src_path = _CONTRACTS_DIR / config_file
            if src_path.exists():
                shutil.copy2(src_path, tmppath / config_file)

        # Use the existing contracts/lib/ directory rather than running
        # `forge install` on every execution (wasteful and requires network).
        lib_src = _CONTRACTS_DIR / "lib"
        lib_dst = tmppath / "lib"
        if lib_src.exists():
            try:
                os.symlink(lib_src, lib_dst)
            except OSError:
                # Fall back to a full copy when symlinks are not supported
                # (e.g., certain CI environments or cross-device links).
                shutil.copytree(lib_src, lib_dst)
        else:
            # If there is no pre-installed lib, write a minimal foundry.toml
            # so forge does not error out on a missing libs directory.
            lib_dst.mkdir()
            (tmppath / "foundry.toml").write_text(
                '[profile.default]\nsrc = "src"\nout = "out"\nlibs = ["lib"]\nsolc = "0.8.24"\n'
            )

        # Use --json for structured, machine-readable output.
        cmd = ["forge", "test", "--fork-url", RPC_URL, "--json"]
        if fork_block:
            cmd.extend(["--fork-block-number", str(fork_block)])

        result = subprocess.run(cmd, cwd=tmpdir, capture_output=True, text=True, timeout=120)

        return parse_forge_output(result.stdout, result.stderr)


def parse_forge_output(stdout: str, stderr: str) -> dict:
    """Parse forge test JSON output for pass/fail and gas usage.

    Forge emits one JSON object per test suite when --json is used.
    Falls back to string matching for legacy/non-JSON output.
    """
    gas_used = 0
    success = False

    # Attempt structured JSON parsing first.
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue

        if not isinstance(data, dict):
            continue

        # Each key is a test-contract path; its value is a dict of test results.
        for _contract, tests in data.items():
            if not isinstance(tests, dict):
                continue
            for _test_name, test_result in tests.items():
                if not isinstance(test_result, dict):
                    continue
                # A single passing test marks the whole run as successful.
                if test_result.get("status") == "success":
                    success = True
                # Accumulate gas across all test results.
                gas_used += test_result.get("gasUsed", 0)

        # Parsed at least one valid JSON object — stop scanning further lines.
        if gas_used > 0 or success:
            break

    # If JSON parsing found nothing (e.g., forge printed non-JSON output),
    # fall back to lightweight string matching so the runner remains useful
    # in environments where --json is not fully supported.
    if not success and gas_used == 0:
        combined = stdout + stderr
        success = "[PASS]" in combined

        import re
        gas_match = re.search(r"\(gas:\s*(\d+)\)", combined)
        if gas_match:
            gas_used = int(gas_match.group(1))

    return {
        "success": success,
        "gas_used": gas_used,
        "stdout": stdout,
        "stderr": stderr,
    }
