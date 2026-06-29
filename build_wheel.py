import subprocess
import sys


def main() -> int:
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "build"], check=True)
        subprocess.run([sys.executable, "-m", "build"], check=True)
    except subprocess.CalledProcessError as exc:
        return exc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
