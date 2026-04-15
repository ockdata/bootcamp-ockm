"""Run a job locally, loading .env if present."""
import subprocess
import sys
from pathlib import Path


def main():
    python = sys.argv[1]
    job = sys.argv[2]

    env_file = Path(".env")
    env = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()

    import os
    full_env = {**os.environ, **env, "PYTHONPATH": "."}

    result = subprocess.run(
        [python, "-m", f"jobs.{job}.main"],
        env=full_env,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
