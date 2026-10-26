"""Build/inspect a disposable Debian binary; never install or publish it.

An optional registered desktop client is injected only into the isolated build
copy. No user token, development database or ignored repository file is copied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-file", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix="pinleaf-package-qa-"))
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    source = root / f"pinleaf-{version}"
    source.mkdir()
    tracked = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT).decode().split("\0")
    for name in tracked:
        if not name or not (ROOT / name).exists():
            continue
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target, follow_symlinks=False)
    if args.client_file is not None:
        import sys
        sys.path.insert(0, str(ROOT))
        from pinleaf.services.drive_auth import client_configuration
        os.environ["PINLEAF_GOOGLE_CLIENT_FILE"] = str(args.client_file.resolve())
        public_client = client_configuration()
        (source / "pinleaf/resources/google-client.json").write_text(json.dumps(public_client) + "\n")
    log = root / "build.log"
    with log.open("w") as output:
        built = subprocess.run(["dpkg-buildpackage", "-us", "-uc", "-b"], cwd=source, stdout=output, stderr=subprocess.STDOUT)
    if built.returncode:
        print("\n".join(log.read_text().splitlines()[-60:]))
        raise SystemExit(built.returncode)
    artifacts = list(root.glob("pinleaf_*.deb"))
    assert len(artifacts) == 1
    artifact = artifacts[0]
    package_version = subprocess.check_output(["dpkg-deb", "-f", str(artifact), "Version"], text=True).strip()
    assert package_version == version, (package_version, version)
    unpacked = root / "unpacked"
    subprocess.run(["dpkg-deb", "-x", str(artifact), str(unpacked)], check=True)
    package = unpacked / "usr/lib/python3/dist-packages/pinleaf"
    for name in ("resources/backup/backup-envelope.schema.json", "resources/backup/backup-payload.schema.json",
                 "services/drive_auth.py", "services/drive_backup.py", "ui/backup_window.py"):
        assert (package / name).is_file(), name
    assert not list(package.rglob("*.sqlite3"))
    assert not list(package.rglob("client_secret_*.json"))
    assert (unpacked / "usr/share/man/man1/pinleaf.1.gz").is_file()
    configured = (package / "resources/google-client.json").is_file()
    if configured:
        client = json.loads((package / "resources/google-client.json").read_bytes())
        assert set(client) == {"installed"}
        assert set(client["installed"]) == {"client_id", "client_secret", "auth_uri", "token_uri"}
    environment = dict(os.environ, PYTHONPATH=str(package.parent))
    environment.pop("PINLEAF_GOOGLE_CLIENT_FILE", None)
    if configured:
        subprocess.run(["/usr/bin/python3", "-c", "from pinleaf.services.drive_auth import client_configuration; assert 'installed' in client_configuration(); print('Packaged client loads without development override')"],
                       cwd=root, env=environment, check=True)
    inspected = subprocess.check_output(["dpkg-deb", "-f", str(artifact), "Depends"], text=True).strip()
    linted = subprocess.run(["lintian", "--fail-on", "error,warning", str(artifact)], capture_output=True, text=True)
    result = {"status": "PASS" if linted.returncode == 0 else "FAIL", "version": package_version, "installed": False,
              "published": False, "client_injected_in_build_copy": args.client_file is not None,
              "packaged_client_configured": configured,
              "artifact": str(artifact), "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
              "depends": inspected, "lintian_returncode": linted.returncode,
              "lintian_output": (linted.stdout + linted.stderr).strip()}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    raise SystemExit(linted.returncode)


if __name__ == "__main__":
    main()
