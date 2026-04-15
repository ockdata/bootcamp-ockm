"""Scaffold a new workflow from the generic template."""
import shutil
import sys
from pathlib import Path


def main():
    wf = sys.argv[1]
    src = Path("workflows/daily_pipeline")
    dst = Path(f"workflows/{wf}")

    if dst.exists():
        print(f"Workflow '{wf}' already exists at {dst}")
        sys.exit(1)

    shutil.copytree(src, dst)

    wf_path = dst / "workflow.yaml"
    content = wf_path.read_text()
    content = content.replace("daily-pipeline", wf.replace("_", "-"))
    content = content.replace("Generic daily ETL pipeline", f"Pipeline {wf}")
    wf_path.write_text(content)

    print(f"Workflow '{wf}' created at {dst}")
    print(f"  Edit {dst}/workflow.yaml to define steps.")


if __name__ == "__main__":
    main()
