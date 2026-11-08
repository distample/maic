"""Verify local optional Python modules against the reviewed source snapshot."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "requirements" / "bundled-modules.json"


def digest(path):
    # Normalize text line endings to make Windows/Linux snapshots equivalent.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def check(root=ROOT, apply_patches=False):
    manifest = json.loads((root / "requirements" / "bundled-modules.json").read_text(encoding="utf-8"))
    problems = []
    for module in manifest["modules"]:
        directory = root / module["path"]
        if not directory.is_dir():
            print(f"Optional module absent: {module['path']}")
            continue
        for patch in module.get("patches", []):
            path = directory / patch["file"]
            if path.is_file() and digest(path) == patch["before_sha256"] and apply_patches:
                source = path.read_text(encoding="utf-8")
                if source.count(patch["old"]) != 1:
                    problems.append(f"Patch context mismatch: {path}")
                    continue
                path.write_text(source.replace(patch["old"], patch["new"]), encoding="utf-8")
        actual = {p.relative_to(directory).as_posix(): digest(p) for p in directory.rglob("*.py")}
        expected = module["python_files"]
        for name in sorted(actual.keys() | expected.keys()):
            if actual.get(name) != expected.get(name):
                problems.append(f"Module snapshot mismatch: {module['path']}/{name}")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-patches", action="store_true",
                        help="Apply only checksum-matched, reviewed compatibility patches")
    parser.add_argument("--audit-requirements", type=Path,
                        help="Export vendored package versions for pip-audit")
    args = parser.parse_args(argv)
    if args.audit_requirements:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        specs = sorted({f"{entry['name']}=={entry['version']}"
                        for module in manifest["modules"] for entry in module.get("vendored", [])})
        args.audit_requirements.write_text("\n".join(specs) + "\n", encoding="utf-8")
    problems = check(apply_patches=args.apply_patches)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        print("Restore the recorded module snapshot or review and update its manifest.", file=sys.stderr)
        return 1
    print("Bundled Python modules: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
