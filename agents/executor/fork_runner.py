# agents/executor/fork_runner.py
"""Runs hunter PoC scripts in a Foundry fork."""
import re
import subprocess
import tempfile
from pathlib import Path

from common.config import RPC_URL


def run_poc_in_fork(poc_source: str, fork_block: int | None = None) -> dict:
    """Execute a Foundry PoC test in a forked environment."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create minimal Foundry project
        src_dir = Path(tmpdir) / "src"
        test_dir = Path(tmpdir) / "test"
        src_dir.mkdir()
        test_dir.mkdir()

        (test_dir / "Exploit.t.sol").write_text(poc_source)
        (Path(tmpdir) / "foundry.toml").write_text(
            '[profile.default]\nsrc = "src"\nout = "out"\nlibs = ["lib"]\nsolc = "0.8.24"\n'
        )

        # Install forge-std
        subprocess.run(
            ["forge", "install", "foundry-rs/forge-std", "--no-git", "--no-commit"],
            cwd=tmpdir, capture_output=True,
        )

        cmd = ["forge", "test", "--fork-url", RPC_URL, "-vvv"]
        if fork_block:
            cmd.extend(["--fork-block-number", str(fork_block)])

        result = subprocess.run(cmd, cwd=tmpdir, capture_output=True, text=True, timeout=120)

        return parse_forge_output(result.stdout, result.stderr)


def parse_forge_output(stdout: str, stderr: str) -> dict:
    """Parse forge test output for pass/fail and gas."""
    combined = stdout + stderr
    success = "[PASS]" in combined
    gas_used = 0

    gas_match = re.search(r"\(gas:\s*(\d+)\)", combined)
    if gas_match:
        gas_used = int(gas_match.group(1))

    return {
        "success": success,
        "gas_used": gas_used,
        "stdout": stdout,
        "stderr": stderr,
    }
