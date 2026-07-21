"""Package the bundle into a portable .zip (stdlib only; canonical, Explorer-friendly).

Excludes the rebuildable virtualenv and caches. Run with any Python (e.g. the
bundled one) — it imports nothing from the project, so it never triggers model
downloads. Invoked by make-zip.bat.
"""
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Name the zip after the bundle folder so different bundles don't overwrite each other.
DEST = os.path.join(os.path.dirname(ROOT), os.path.basename(ROOT) + "-offline.zip")
EXCLUDE_DIRS = {".venv", ".venv.dev", ".pytest_cache", "__pycache__", ".git", "logs"}


def main() -> None:
    if os.path.exists(DEST):
        os.remove(DEST)
    count = 0
    with zipfile.ZipFile(DEST, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as z:
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for name in filenames:
                full = os.path.join(dirpath, name)
                if os.path.abspath(full) == os.path.abspath(DEST):
                    continue
                z.write(full, os.path.relpath(full, ROOT))
                count += 1
                if count % 500 == 0:
                    print(f"  {count} files...", flush=True)
    size_gb = os.path.getsize(DEST) / (1024 ** 3)
    print(f"Wrote {DEST} ({count} files, {size_gb:.2f} GB)")


if __name__ == "__main__":
    sys.exit(main())
