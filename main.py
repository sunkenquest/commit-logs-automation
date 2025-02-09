import os
import subprocess
from dotenv import load_dotenv
import pytz
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any

load_dotenv()

PHT = pytz.timezone("Asia/Manila")
since_date_utc = (datetime.utcnow() - timedelta(hours=os.getenv('HOURS'))).replace(tzinfo=pytz.utc).astimezone(PHT)
since_date = since_date_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
BASE_URL = f"https://api.github.com/repos/{os.getenv('REPO_OWNER')}/{os.getenv('REPO_NAME')}"


def get_headers() -> Dict[str, str]:
    """Returns the required headers for GitHub API authentication."""
    return {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {os.getenv('PAT_WORK')}",
    }


def fetch_branches() -> List[str]:
    """Fetches all branches in the repository."""
    url = f"{BASE_URL}/branches"
    response = requests.get(url, headers=get_headers())

    if response.status_code == 200:
        return [branch["name"] for branch in response.json()]
    else:
        print(f"Failed to fetch branches: {response.status_code}")
        print(response.json())
        return []


def fetch_commits(branch: str) -> List[Dict[str, Any]]:
    """Fetches commits from a specific branch in the past 7 days."""
    url = f"{BASE_URL}/commits"
    params = {"sha": branch, "since": since_date}
    
    response = requests.get(url, headers=get_headers(), params=params)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch commits for branch {branch}: {response.status_code}")
        print(response.json())
        return []


def filter_commits_by_author(commits: List[Dict[str, Any]], author_name: str) -> List[Dict[str, Any]]:
    """Filters commits authored by a specific person."""
    return [
        commit for commit in commits
        if commit.get("commit", {}).get("author", {}).get("name") == author_name
    ]

def write_to_log(commits: List[Dict[str, Any]], log_file: str = "project-commits.logs"):
    """Writes commit details to a log file and commits each entry separately."""

    git_user = os.getenv("GIT_USER", "github-actions[bot]")
    git_email = os.getenv("GIT_EMAIL", "github-actions[bot]@users.noreply.github.com")
    
    subprocess.run(["git", "config", "--global", "user.name", git_user], check=True)
    subprocess.run(["git", "config", "--global", "user.email", git_email], check=True)

    for commit in commits:
        project = os.getenv('REPO_NAME')
        sha = commit.get("sha", "N/A")
        message = commit.get("commit", {}).get("message", "No message")
        author_info = commit.get("commit", {}).get("author", {})
        date = author_info.get("date", "Unknown")
        branch = commit["branch"]

        log_entry = (
            f"Project: {project}\nBranch: {branch}\nSHA: {sha}\n"
            f"Date: {date}\nMessage: {message}\n{'-' * 50}\n\n"
        )

        with open(log_file, "a") as file:
            file.write(log_entry)

        commit_message = f"📜 Log commit {sha[:7]} - {message.splitlines()[0]}"
        subprocess.run(["git", "add", log_file], check=True)
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
    
    subprocess.run(["git", "push"], check=True)

def main():
    """Main function to fetch and display commits from all branches by the specified author."""
    branches = fetch_branches()
    if not branches:
        print("No branches found or failed to fetch.")
        return

    all_author_commits = []
    for branch in branches:
        commits = fetch_commits(branch)
        author_commits = filter_commits_by_author(commits, os.getenv('AUTHOR_NAME'))

        for commit in author_commits:
            commit["branch"] = branch
            all_author_commits.append(commit)

    if not all_author_commits:
        print(f"No commits found by {os.getenv('AUTHOR_NAME')} in the last 7 days across all branches.")
        return

    write_to_log(all_author_commits)

    print(f"✅ {len(all_author_commits)} commits written to project-commits.logs.")
if __name__ == "__main__":
    main()
