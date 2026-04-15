"""Validate all workflow.yaml definitions."""
import yaml
from pathlib import Path


def validate(workflow_path: Path) -> bool:
    with open(workflow_path) as f:
        data = yaml.safe_load(f)
    required = {"name", "description", "schedule"}
    missing = required - set(data.get("workflow", {}).keys())
    if missing:
        print(f"[FAIL] {workflow_path}: missing fields {missing}")
        return False
    print(f"[OK] {workflow_path}")
    return True


if __name__ == "__main__":
    root = Path(__file__).parent.parent / "workflows"
    results = [validate(p) for p in root.rglob("workflow.yaml")]
    if not all(results):
        raise SystemExit(1)
