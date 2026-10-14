"""Optional authorized GitHub publisher. Never prints or stores Git credentials.

Uses existing Git Credential Manager authorization only; non-interactive.
No overwrite of existing repositories. Use --probe to test capability.
"""
import argparse
import os
import subprocess
from pathlib import Path
import httpx

root = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="Never")
    result = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
                            text=True, capture_output=True, env=env, timeout=30)
    credentials = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    token = credentials.get("password")
    if result.returncode or not token:
        print("NO_GITHUB_PUSH_CREDENTIAL: Git Credential Manager has no usable non-interactive GitHub authorization.")
        return 2
    with httpx.Client(headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}, timeout=30, follow_redirects=False) as client:
        user = client.get("https://api.github.com/user")
        if user.status_code != 200:
            print(f"GITHUB_AUTH_UNAVAILABLE: HTTP {user.status_code}")
            return 2
        login = user.json()["login"]
        print(f"GITHUB_AUTH_AVAILABLE: {login}")
        if args.probe:
            return 0
        # Whitelist tracked source: no private documents, credentials or build products.
        files = subprocess.check_output(["git", "ls-files"], cwd=root, text=True).splitlines()
        forbidden = (".pdf", ".docx", ".doc", ".log")
        if any(name.lower().endswith(forbidden) or name.startswith((".venv/", "scratch/", "dist/", "release/")) or name in ("settings.json", "config.json", ".env") for name in files):
            raise RuntimeError("Tracked private/build data detected; publishing stopped.")
        if subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip():
            raise RuntimeError("Commit all reviewed source before publishing.")
        created = client.post("https://api.github.com/user/repos", json={"name": "document-studio", "private": False,
                              "description": "Windows Word/PDF desktop tools and cloud document translation", "auto_init": False})
        if created.status_code != 201:
            print(f"REPOSITORY_NOT_CREATED: HTTP {created.status_code}; existing repositories are not modified.")
            return 3
        url = created.json()["html_url"]
        subprocess.run(["git", "remote", "add", "origin", url + ".git"], cwd=root, check=True, env=env)
        subprocess.run(["git", "push", "-u", "origin", "main"], cwd=root, check=True, env=env)
        subprocess.run(["git", "tag", "v0.1.0"], cwd=root, check=True, env=env)
        subprocess.run(["git", "push", "origin", "v0.1.0"], cwd=root, check=True, env=env)
        print(f"PUBLISHED_SOURCE: {url}; release build queued by tag push.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
