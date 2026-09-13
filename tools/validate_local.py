from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BLENDER_WINDOWS = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
GPU_FREE_SMOKES = (
    ("semantic_refinement", "tests/blender_runtime/run_refinement_smoke.py", "SEMANTIC_REFINEMENT_SMOKE: PASS"),
    ("window_capability", "tests/blender_runtime/run_window_capability_smoke.py", "WINDOW_CAPABILITY_SMOKE: PASS"),
    ("transform_safety", "tests/blender_runtime/run_transform_safety.py", "TRANSFORM_SAFETY: PASS"),
    ("batch_cleanup", "tests/blender_runtime/run_cleanup_smoke.py", "CLEANUP_SMOKE: PASS"),
    ("export_state", "tests/blender_runtime/run_export_state_smoke.py", "EXPORT_STATE_SMOKE: PASS"),
    ("mobile_lod", "tests/blender_runtime/run_lod_smoke.py", "LOD_SMOKE: PASS"),
    ("batch_provenance", "tests/blender_runtime/run_batch_provenance_smoke.py", "BATCH_PROVENANCE_SMOKE: PASS"),
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Axion Family Creator local validation gates without GitHub Actions."
    )
    parser.add_argument(
        "--blender",
        help="Path to Blender executable. Defaults to Blender 5.2 Windows path, then PATH lookup.",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Also run tests/blender_runtime/run_all.py, which includes thumbnail rendering.",
    )
    parser.add_argument("--skip-pure", action="store_true", help="Skip normal Python unittest discovery.")
    parser.add_argument("--skip-smokes", action="store_true", help="Skip focused GPU-free Blender smokes.")
    parser.add_argument(
        "--real-input",
        help="Optional real-asset corpus directory. Runs run_real_assets.py with --no-thumbnail.",
    )
    parser.add_argument(
        "--real-output",
        help="Output directory for --real-input. Required when --real-input is used.",
    )
    parser.add_argument(
        "--real-family-class",
        default="AUTO_FOLDER",
        help="Exact Family Class or AUTO_FOLDER for the optional real-asset pass.",
    )
    parser.add_argument(
        "--baseline-hardening",
        help="Optional golden hardening-report.json to compare after --real-input.",
    )
    parser.add_argument(
        "--report",
        default="tests/blender_runtime/artifacts/local-validation.json",
        help="JSON summary path relative to repo root unless absolute.",
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="Continue after failed gates so the report contains all failures.",
    )
    return parser.parse_args()


def resolve_blender(explicit=None):
    if explicit:
        path = Path(explicit).expanduser()
        if path.is_file():
            return path.resolve()
        resolved = shutil.which(str(explicit))
        if resolved:
            return Path(resolved).resolve()
        raise FileNotFoundError(f"Blender executable not found: {explicit}")

    if DEFAULT_BLENDER_WINDOWS.is_file():
        return DEFAULT_BLENDER_WINDOWS

    resolved = shutil.which("blender")
    if resolved:
        return Path(resolved).resolve()
    raise FileNotFoundError(
        "Blender executable not found. Pass --blender or install Blender 5.2 in the standard location."
    )


def _probe(command, cwd=REPO_ROOT):
    try:
        completed = subprocess.run(
            [str(value) for value in command],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=15,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    return (completed.stdout or "").strip()


def _runtime_metadata(blender):
    git_commit = _probe(["git", "rev-parse", "HEAD"])
    git_status = _probe(["git", "status", "--porcelain"])
    blender_version_output = _probe([blender, "--version"])
    blender_version = None
    if blender_version_output:
        blender_version = blender_version_output.splitlines()[0].strip()
    return {
        "gitCommit": git_commit.splitlines()[0].strip() if git_commit else None,
        "gitDirty": bool(git_status) if git_status is not None else None,
        "pythonVersion": sys.version.splitlines()[0],
        "blenderVersion": blender_version,
    }


def run_command(name, command, expected_marker=None, cwd=REPO_ROOT):
    started = time.time()
    completed = subprocess.run(
        [str(value) for value in command],
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = completed.stdout or ""
    marker_ok = expected_marker is None or expected_marker in output
    passed = completed.returncode == 0 and marker_ok
    result = {
        "name": name,
        "passed": passed,
        "returnCode": int(completed.returncode),
        "durationSeconds": round(time.time() - started, 3),
        "command": [str(value) for value in command],
        "expectedMarker": expected_marker,
        "markerFound": marker_ok if expected_marker is not None else None,
        "outputTail": output[-12000:],
    }
    print(f"[{'PASS' if passed else 'FAIL'}] {name} ({result['durationSeconds']}s)")
    if not passed:
        print(result["outputTail"])
    return result


def blender_python_command(blender, script, extra_args=None):
    command = [
        blender,
        "--background",
        "--factory-startup",
        "--python",
        REPO_ROOT / script,
    ]
    if extra_args:
        command.append("--")
        command.extend(extra_args)
    return command


def write_report(path, payload):
    report_path = Path(path)
    if not report_path.is_absolute():
        report_path = REPO_ROOT / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return report_path


def should_stop(result, keep_going):
    return not result.get("passed", False) and not keep_going


def stop_with_report(args, report):
    report["passed"] = False
    report["gateCount"] = len(report.get("gates", ()))
    report["passedCount"] = sum(1 for gate in report.get("gates", ()) if gate.get("passed"))
    report["failedCount"] = report["gateCount"] - report["passedCount"]
    report_path = write_report(args.report, report)
    print(f"Validation report: {report_path}")
    raise SystemExit(1)


def main():
    args = parse_args()
    blender = resolve_blender(args.blender)
    runtime = _runtime_metadata(blender)
    report = {
        "schema": "axion.family.local-validation",
        "schemaVersion": 1,
        "repoRoot": str(REPO_ROOT),
        "python": sys.executable,
        "blender": str(blender),
        "gitCommit": runtime["gitCommit"],
        "gitDirty": runtime["gitDirty"],
        "pythonVersion": runtime["pythonVersion"],
        "blenderVersion": runtime["blenderVersion"],
        "mode": "full" if args.full else "gpu-safe",
        "gates": [],
    }

    if not args.skip_pure:
        result = run_command(
            "pure_python",
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        )
        report["gates"].append(result)
        if should_stop(result, args.keep_going):
            stop_with_report(args, report)

    if not args.skip_smokes:
        for name, script, marker in GPU_FREE_SMOKES:
            result = run_command(name, blender_python_command(blender, script), marker)
            report["gates"].append(result)
            if should_stop(result, args.keep_going):
                stop_with_report(args, report)

    if args.full:
        result = run_command(
            "full_blender_runtime",
            blender_python_command(blender, "tests/blender_runtime/run_all.py"),
        )
        report["gates"].append(result)
        if should_stop(result, args.keep_going):
            stop_with_report(args, report)

    if args.real_input:
        if not args.real_output:
            raise SystemExit("--real-output is required when --real-input is provided")
        real_input = Path(args.real_input).expanduser().resolve()
        real_output = Path(args.real_output).expanduser().resolve()
        if not real_input.is_dir():
            raise SystemExit(f"Real-asset input does not exist: {real_input}")
        real_output.mkdir(parents=True, exist_ok=True)

        extra = [
            "--input", str(real_input),
            "--output", str(real_output),
            "--family-class", str(args.real_family_class).upper(),
            "--no-thumbnail",
        ]
        result = run_command(
            "real_assets_gpu_safe",
            blender_python_command(blender, "tests/blender_runtime/run_real_assets.py", extra),
        )
        result["hardeningReport"] = str(real_output / "hardening-report.json")
        report["gates"].append(result)
        if should_stop(result, args.keep_going):
            stop_with_report(args, report)

        if args.baseline_hardening and result.get("passed"):
            baseline = Path(args.baseline_hardening).expanduser().resolve()
            candidate = real_output / "hardening-report.json"
            compare_output = real_output / "hardening-compare.json"
            compare = run_command(
                "hardening_compare",
                [
                    sys.executable,
                    "tools/compare_hardening.py",
                    "--baseline", baseline,
                    "--candidate", candidate,
                    "--output", compare_output,
                    "--fail-on-regression",
                ],
            )
            compare["comparisonReport"] = str(compare_output)
            report["gates"].append(compare)
            if should_stop(compare, args.keep_going):
                stop_with_report(args, report)

    report["passed"] = all(gate.get("passed", False) for gate in report["gates"])
    report["gateCount"] = len(report["gates"])
    report["passedCount"] = sum(1 for gate in report["gates"] if gate.get("passed"))
    report["failedCount"] = report["gateCount"] - report["passedCount"]
    report_path = write_report(args.report, report)

    print("\n=== Axion Local Validation ===")
    print(f"Commit: {report.get('gitCommit') or 'unknown'}")
    print(f"Dirty working tree: {report.get('gitDirty')}")
    print(f"Blender: {report.get('blenderVersion') or blender}")
    print(f"Passed: {report['passedCount']}/{report['gateCount']}")
    print(f"Mode: {report['mode']}")
    print(f"Report: {report_path}")
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
