"""Compare two Axion real-asset hardening reports.

Example:

python tools/compare_hardening.py \
  --baseline D:\\baseline\\hardening-report.json \
  --candidate D:\\expanded\\hardening-report.json \
  --output D:\\expanded\\hardening-compare.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hardening_compare import compare_hardening_reports


def parse_args():
    parser = argparse.ArgumentParser(description="Compare Axion hardening reports")
    parser.add_argument("--baseline", required=True, help="Previous/golden hardening-report.json")
    parser.add_argument("--candidate", required=True, help="New/expanded hardening-report.json")
    parser.add_argument("--output", help="Optional JSON output path; defaults beside candidate")
    return parser.parse_args()


def load_json(path):
    return json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8"))


def main():
    args = parse_args()
    baseline_path = Path(args.baseline).expanduser().resolve()
    candidate_path = Path(args.candidate).expanduser().resolve()
    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else candidate_path.with_name("hardening-compare.json")
    )

    result = compare_hardening_reports(load_json(baseline_path), load_json(candidate_path))
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    candidate = result["candidate"]
    new_assets = result["newAssets"]
    gate = result["gate"]
    corpus = result["corpus"]

    print("=== Axion Hardening Compare ===")
    print(f"Baseline: {baseline_path}")
    print(f"Candidate: {candidate_path}")
    print(f"Overlap assets: {corpus['overlapCount']}")
    print(f"New assets: {corpus['newCount']}")
    print(f"Removed assets: {corpus['removedCount']}")
    print(f"Candidate conversion success: {candidate['conversionSuccessRate']:.1%}")
    print(f"Candidate auto acceptance: {candidate['autoAcceptanceRate']:.1%}")
    print(f"New-asset auto acceptance: {new_assets['autoAcceptanceRate']:.1%}")
    print(f"Overlap regressions: {gate['overlapRegressionCount']}")
    print(f"Asset-key collisions: {gate.get('assetKeyCollisionCount', 0)}")
    print(f"No-regression gate: {'PASS' if gate['passesNoRegressionGate'] else 'FAIL'}")
    print(f"Output: {output_path}")

    if result["overlap"]["regressions"]:
        print("Overlap regressions:")
        for item in result["overlap"]["regressions"]:
            print(f"  {item['assetKey']}: {item['regression']}")

    for label, collisions in (
        ("Baseline key collisions", corpus.get("baselineKeyCollisions", {})),
        ("Candidate key collisions", corpus.get("candidateKeyCollisions", {})),
    ):
        if not collisions:
            continue
        print(label + ":")
        for key, sources in collisions.items():
            print(f"  {key}")
            for source in sources:
                print(f"    {source}")


if __name__ == "__main__":
    main()
