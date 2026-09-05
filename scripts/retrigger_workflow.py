import os
import sys
import time
from datetime import datetime, timezone, timedelta
import requests

GITHUB_API_URL = "https://api.github.com"

def retrigger():
    pat = os.getenv("GH_PAT") or os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")
    workflow_id = os.getenv("WORKFLOW_ID", "server.yml")
    ref = os.getenv("GITHUB_REF_NAME", "main")

    if not pat or not repo:
        print("[INFO] No GH_PAT token or repository. Retrigger skipped.")
        return

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {pat}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        runs_url = f"{GITHUB_API_URL}/repos/{repo}/actions/workflows/{workflow_id}/runs"
        resp = requests.get(runs_url, headers=headers, params={"status": "in_progress", "per_page": 5}, timeout=15)
        if resp.status_code == 200:
            in_prog = resp.json().get("workflow_runs", [])
            curr_id = os.getenv("GITHUB_RUN_ID")
            others = [r for r in in_prog if str(r.get("id")) != str(curr_id)]
            if others:
                print(f"[GUARD] Active workflow run already exists. Skipping trigger.")
                return

        dispatch_url = f"{GITHUB_API_URL}/repos/{repo}/actions/workflows/{workflow_id}/dispatches"
        dispatch_resp = requests.post(dispatch_url, headers=headers, json={"ref": ref}, timeout=15)
        if dispatch_resp.status_code == 204:
            print("[SUCCESS] New workflow run dispatched successfully.")
        else:
            print(f"[INFO] Dispatch response: HTTP {dispatch_resp.status_code}")
    except Exception as e:
        print(f"[ERROR] Retrigger error: {e}")

if __name__ == "__main__":
    retrigger()
