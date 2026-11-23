"""Python entrypoint for syncdap CLI when installed via uv tool or pip."""

import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    src_dir = Path(__file__).resolve().parent
    base_dir = src_dir.parent

    # Find the shell coordinator runner
    runner = None
    for cand in [
        src_dir / "sh" / "main.sh",
        base_dir / "syncdap",
        base_dir / "src" / "sh" / "main.sh",
    ]:
        if cand.is_file():
            runner = cand
            break

    if not runner:
        print(f"Error: syncdap coordinator not found in {src_dir}", file=sys.stderr)
        sys.exit(1)

    env = os.environ.copy()
    env["SYNCDAP_PYTHON"] = sys.executable
    env["SCRIPT_DIR"] = str(base_dir)
    env["PYTHONPATH"] = f"{base_dir}:{env.get('PYTHONPATH', '')}".rstrip(":")

    try:
        res = subprocess.run(["bash", str(runner), *sys.argv[1:]], env=env)
        sys.exit(res.returncode)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
