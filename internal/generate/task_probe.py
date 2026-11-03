#!/usr/bin/env python3
"""Replay generator diagnostics with a controlled go-mod-tidy child."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


BASE, HEAD, LOG_DIR = sys.argv[1:]
LOG_DIR = Path(LOG_DIR).resolve()
LOG_DIR.mkdir(parents=True, exist_ok=True)
REPO = Path.cwd()
GO = shutil.which("go")
assert GO, "an existing Go toolchain is required"
STDOUT_MARKER = "controlled tidy stdout"
STDERR_MARKER = "controlled tidy stderr"


def git(*args):
    return subprocess.run(
        ["git", *args], cwd=REPO, check=True, capture_output=True
    ).stdout


def replay(label, revision, child_exit):
    with tempfile.TemporaryDirectory(prefix="opendal-go-generator-") as directory:
        root = Path(directory)
        for relative in git(
            "ls-tree", "-r", "--name-only", revision, "--", "internal/generate"
        ).decode().splitlines():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(git("show", f"{revision}:{relative}"))

        workspace = root / "workspace"
        module = workspace / "webdav"
        incoming = workspace / "libopendal_c_latest_webdav_linux"
        incoming.mkdir(parents=True)
        (incoming / "libopendal_c.linux.so.zst").write_bytes(b"generator rename probe")
        fake_bin = root / "bin"
        fake_bin.mkdir()
        fake_go = fake_bin / "go"
        fake_go.write_text(
            '#!/bin/sh\n'
            'test "$1" = mod && test "$2" = tidy || exit 98\n'
            'test "$PWD" = "$EXPECTED_TIDY_DIR" || exit 99\n'
            'printf "%s\\n" "$PROBE_STDOUT"\n'
            'printf "%s\\n" "$PROBE_STDERR" >&2\n'
            'exit "$PROBE_EXIT"\n'
        )
        fake_go.chmod(0o755)
        env = os.environ.copy()
        env.update(
            PATH=str(fake_bin) + os.pathsep + env["PATH"],
            GITHUB_WORKSPACE=str(workspace),
            VERSION="latest",
            MATRIX=json.dumps(
                {
                    "build": [{"target": "linux", "goos": "linux", "goarch": "amd64"}],
                    "service": ["webdav"],
                }
            ),
            GOTOOLCHAIN="local",
            GOWORK="off",
            CGO_ENABLED="0",
            GOMAXPROCS="4",
            EXPECTED_TIDY_DIR=str(module),
            PROBE_STDOUT=STDOUT_MARKER,
            PROBE_STDERR=STDERR_MARKER,
            PROBE_EXIT=str(child_exit),
        )
        binary = root / "generator"
        build_env = env.copy()
        build_env["PATH"] = os.environ["PATH"]
        build = subprocess.run(
            [GO, "build", "-o", str(binary), "generate.go"],
            cwd=root / "internal/generate",
            env=build_env,
            capture_output=True,
            text=True,
        )
        (LOG_DIR / f"{label}.build.stdout").write_text(build.stdout)
        (LOG_DIR / f"{label}.build.stderr").write_text(build.stderr)
        (LOG_DIR / f"{label}.build.exit").write_text(f"{build.returncode}\n")
        assert build.returncode == 0, (label, build.stderr)
        # go run prepends GOROOT/bin to PATH, hiding the controlled tidy child.
        result = subprocess.run(
            [str(binary)],
            cwd=root / "internal/generate",
            env=env,
            capture_output=True,
            text=True,
        )
        (LOG_DIR / f"{label}.stdout").write_text(result.stdout)
        (LOG_DIR / f"{label}.stderr").write_text(result.stderr)
        (LOG_DIR / f"{label}.exit").write_text(f"{result.returncode}\n")
        combined = result.stdout + result.stderr
        if child_exit:
            assert result.returncode != 0, label
            assert "exit status 17" in result.stderr, (label, result.stderr)
            if revision == BASE:
                assert STDOUT_MARKER not in combined and STDERR_MARKER not in combined
            else:
                assert STDOUT_MARKER in result.stdout and STDERR_MARKER in result.stderr
                assert f"go mod tidy in {module}: exit status 17" in result.stderr
        else:
            assert result.returncode == 0, (label, result.stderr)
            assert STDOUT_MARKER in result.stdout
            if revision == HEAD:
                assert STDERR_MARKER in result.stderr
        outputs = {
            str(file.relative_to(module)): hashlib.sha256(file.read_bytes()).hexdigest()
            for file in sorted(module.rglob("*"))
            if file.is_file()
        }
        assert outputs, label
        return {
            "revision": revision,
            "build_exit": build.returncode,
            "exit": result.returncode,
            "controlled_child_exit": child_exit,
            "stdout_visible": STDOUT_MARKER in result.stdout,
            "stderr_visible": STDERR_MARKER in result.stderr,
            "output_files": outputs,
        }


results = {
    "baseline_failure": replay("baseline-failure", BASE, 17),
    "fixed_failure": replay("fixed-failure", HEAD, 17),
    "baseline_success": replay("baseline-success", BASE, 0),
    "fixed_success": replay("fixed-success", HEAD, 0),
}
assert results["baseline_success"]["output_files"] == results["fixed_success"]["output_files"]
results["go_version"] = subprocess.run(
    [GO, "version"], check=True, capture_output=True, text=True
).stdout.strip()
results["execution"] = "Go build followed by direct generator binary execution"
results["status"] = "four generator CLI replays passed"
(LOG_DIR / "results.json").write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps(results, indent=2))
