#!/usr/bin/env python3
"""
Close all open issues in a GitHub repository to reset for testing.

Usage:
    python clear_issues.py
    python clear_issues.py --repo owner/repo
    python clear_issues.py --delete  # WARNING: Permanently deletes issues
"""

import os
import argparse
import warnings

# Suppress SSL warnings on macOS (must be before imports)
warnings.filterwarnings('ignore', category=Warning)

from github import Github, GithubException, Auth


def close_all_issues(repo_name: str, github_token: str, delete: bool = False) -> None:
    """
    Close (or delete) all open issues in the specified repository.
    
    Args:
        repo_name: Repository in format "owner/repo"
        github_token: GitHub personal access token
        delete: If True, delete issues instead of closing them (WARNING: permanent)
    """
    try:
        # Initialize GitHub client
        auth = Auth.Token(github_token)
        g = Github(auth=auth)
        repo = g.get_repo(repo_name)
        
        print(f"Target repository: {repo_name}")
        
        # Get all open issues
        open_issues = list(repo.get_issues(state='open'))
        
        if not open_issues:
            print("No open issues found")
            return
        
        action = "delete" if delete else "close"
        print(f"Found {len(open_issues)} open issues")
        
        # Confirm action
        if delete:
            print("\nWARNING: You are about to PERMANENTLY DELETE all issues.")
            print("This action cannot be undone.")
            confirm = input("Type 'DELETE' to confirm: ")
            if confirm != "DELETE":
                print("Aborted")
                return
        else:
            confirm = input(f"\n{action.capitalize()} all {len(open_issues)} issues? (y/N): ")
            if confirm.lower() != 'y':
                print("Aborted")
                return
        
        print(f"\n{action.capitalize()}ing issues...")
        
        closed_count = 0
        failed_count = 0
        
        for issue in open_issues:
            try:
                if delete:
                    # Note: GitHub API doesn't support deleting issues via PyGithub
                    # This would require using the GraphQL API or REST API directly
                    print(f"  Issue #{issue.number}: Delete not supported via API")
                    print("  Use GitHub UI to delete issues manually")
                    failed_count += 1
                else:
                    issue.edit(state='closed')
                    print(f"  Closed issue #{issue.number}: {issue.title}")
                    closed_count += 1
                    
            except GithubException as e:
                print(f"  Failed to {action} issue #{issue.number}: {e.data.get('message', str(e))}")
                failed_count += 1
        
        print(f"\nCompleted:")
        print(f"  {action.capitalize()}d: {closed_count}")
        if failed_count > 0:
            print(f"  Failed: {failed_count}")
        
    except GithubException as e:
        print(f"Error accessing repository: {e.data.get('message', str(e))}")
        print("\nPossible issues:")
        print("  - Repository doesn't exist or is private")
        print("  - GitHub token doesn't have 'repo' or 'public_repo' scope")
        print("  - Token doesn't have write access to the repository")
        exit(1)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Close all open issues in a GitHub repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python clear_issues.py
  python clear_issues.py --repo aniketm3/demo-targetIssues
  
Environment Variables:
  GITHUB_TOKEN    GitHub personal access token (required)
  TARGET_REPO     Default repository in format "owner/repo"
        """
    )
    
    parser.add_argument(
        "--repo",
        type=str,
        help='Repository in format "owner/repo" (e.g., "aniketm3/demo-targetIssues")'
    )
    
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete issues instead of closing (WARNING: permanent, requires manual action)"
    )
    
    args = parser.parse_args()
    
    # Get GitHub token from environment
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable not set")
        print("\nTo fix this:")
        print("  1. Create a GitHub Personal Access Token at:")
        print("     https://github.com/settings/tokens/new")
        print("  2. Grant 'repo' or 'public_repo' scope")
        print("  3. Export the token: export GITHUB_TOKEN='your_token_here'")
        exit(1)
    
    # Get repository name
    repo_name = args.repo or os.getenv("TARGET_REPO")
    if not repo_name:
        print("Error: Repository not specified")
        print("\nProvide repository using either:")
        print("  --repo flag: python clear_issues.py --repo owner/repo")
        print("  TARGET_REPO env var: export TARGET_REPO='owner/repo'")
        exit(1)
    
    # Validate repository format
    if "/" not in repo_name:
        print(f"Error: Invalid repository format: {repo_name}")
        print('  Expected format: "owner/repo" (e.g., "aniketm3/demo-targetIssues")')
        exit(1)
    
    close_all_issues(repo_name, github_token, args.delete)


if __name__ == "__main__":
    main()
