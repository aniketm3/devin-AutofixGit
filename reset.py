#!/usr/bin/env python3
"""
Reset GitHub repository by closing issues and/or pull requests, and optionally stop Devin sessions.

Usage:
    python reset.py --issues              # Close only issues
    python reset.py --prs                 # Close only PRs
    python reset.py --all                 # Close both issues and PRs
    python reset.py --all --devin         # Close issues/PRs and stop Devin sessions
    python reset.py --all --repo owner/repo
"""

import os
import argparse
import warnings

# Suppress SSL warnings on macOS (must be before imports)
warnings.filterwarnings('ignore', category=Warning)

from github import Github, GithubException, Auth
from src.config import Config
from src.devin_client import DevinClient
from src.state_manager import StateManager


def close_issues(repo, confirm: bool = True) -> tuple[int, int]:
    """
    Close all open issues in the repository.
    
    Args:
        repo: GitHub repository object
        confirm: If True, ask for confirmation before closing
        
    Returns:
        Tuple of (closed_count, failed_count)
    """
    # Get all open issues (excluding PRs)
    open_issues = [issue for issue in repo.get_issues(state='open') if not issue.pull_request]
    
    if not open_issues:
        print("No open issues found")
        return 0, 0
    
    print(f"Found {len(open_issues)} open issues")
    
    if confirm:
        response = input(f"\nClose all {len(open_issues)} issues? (y/N): ")
        if response.lower() != 'y':
            print("Aborted")
            return 0, 0
    
    print("\nClosing issues...")
    
    closed_count = 0
    failed_count = 0
    
    for issue in open_issues:
        try:
            issue.edit(state='closed')
            print(f"  Closed issue #{issue.number}: {issue.title}")
            closed_count += 1
        except GithubException as e:
            print(f"  Failed to close issue #{issue.number}: {e.data.get('message', str(e))}")
            failed_count += 1
    
    return closed_count, failed_count


def close_pull_requests(repo, confirm: bool = True) -> tuple[int, int]:
    """
    Close all open pull requests in the repository.
    
    Args:
        repo: GitHub repository object
        confirm: If True, ask for confirmation before closing
        
    Returns:
        Tuple of (closed_count, failed_count)
    """
    open_prs = list(repo.get_pulls(state='open'))
    
    if not open_prs:
        print("No open pull requests found")
        return 0, 0
    
    print(f"Found {len(open_prs)} open pull requests")
    
    if confirm:
        response = input(f"\nClose all {len(open_prs)} pull requests? (y/N): ")
        if response.lower() != 'y':
            print("Aborted")
            return 0, 0
    
    print("\nClosing pull requests...")
    
    closed_count = 0
    failed_count = 0
    
    for pr in open_prs:
        try:
            pr.edit(state='closed')
            print(f"  Closed PR #{pr.number}: {pr.title}")
            closed_count += 1
        except GithubException as e:
            print(f"  Failed to close PR #{pr.number}: {e.data.get('message', str(e))}")
            failed_count += 1
    
    return closed_count, failed_count


def stop_devin_sessions() -> None:
    """Stop all active Devin sessions and clean up state."""
    try:
        # Load only what we need for Devin operations
        devin_api_key = os.getenv("DEVIN_API_KEY")
        devin_org_id = os.getenv("DEVIN_ORG_ID")
        state_file = os.getenv("STATE_FILE", "state.json")
        
        if not devin_api_key or not devin_org_id:
            print("Error: DEVIN_API_KEY and DEVIN_ORG_ID environment variables are required")
            return
        
        devin = DevinClient(devin_api_key, devin_org_id)
        state = StateManager(state_file)
        
        sessions = state.state.get("devin_sessions", {})
        
        if not sessions:
            print("No Devin sessions found")
            return
        
        # Separate active and inactive sessions
        active_sessions = {}
        inactive_sessions = {}
        
        for issue_num_str, session_data in sessions.items():
            if session_data['status'] in ['exit', 'error', 'suspended']:
                inactive_sessions[issue_num_str] = session_data
            else:
                active_sessions[issue_num_str] = session_data
        
        print(f"Found {len(sessions)} Devin session(s)")
        if active_sessions:
            print(f"  Active: {len(active_sessions)}")
        if inactive_sessions:
            print(f"  Inactive/Suspended: {len(inactive_sessions)}")
        
        response = input(f"\nStop active sessions and clear all from state? (y/N): ")
        if response.lower() != 'y':
            print("Aborted")
            return
        
        print("\nProcessing Devin sessions...")
        
        stopped_count = 0
        cleared_count = 0
        
        # Stop active sessions
        for issue_num_str, session_data in active_sessions.items():
            issue_num = int(issue_num_str)
            session_id = session_data["session_id"]
            
            if devin.stop_session(session_id):
                print(f"  Stopped active session for issue #{issue_num}")
                stopped_count += 1
        
        # Clear all sessions from state
        state.state["devin_sessions"] = {}
        state.save()
        cleared_count = len(sessions)
        
        print(f"\nStopped {stopped_count} active session(s)")
        print(f"Cleared {cleared_count} session(s) from state")
        
    except Exception as e:
        print(f"Error stopping Devin sessions: {e}")


def reset_repository(repo_name: str, github_token: str, close_issues_flag: bool, 
                     close_prs_flag: bool, close_all_flag: bool, stop_devin_flag: bool) -> None:
    """
    Reset repository by closing issues and/or pull requests.
    
    Args:
        repo_name: Repository in format "owner/repo"
        github_token: GitHub personal access token
        close_issues_flag: If True, close all issues
        close_prs_flag: If True, close all PRs
        close_all_flag: If True, close both issues and PRs
        stop_devin_flag: If True, stop all Devin sessions
    """
    try:
        # Initialize GitHub client
        auth = Auth.Token(github_token)
        g = Github(auth=auth)
        repo = g.get_repo(repo_name)
        
        print(f"Target repository: {repo_name}\n")
        
        # Determine what to close
        should_close_issues = close_issues_flag or close_all_flag
        should_close_prs = close_prs_flag or close_all_flag
        should_stop_devin = stop_devin_flag or close_all_flag
        
        total_closed = 0
        total_failed = 0
        
        # Stop Devin sessions first if requested or if --all flag is used
        if should_stop_devin:
            print("=" * 50)
            print("DEVIN SESSIONS")
            print("=" * 50)
            stop_devin_sessions()
            print()
        
        # Close issues
        if should_close_issues:
            print("=" * 50)
            print("ISSUES")
            print("=" * 50)
            closed, failed = close_issues(repo, confirm=True)
            total_closed += closed
            total_failed += failed
            print()
        
        # Close PRs
        if should_close_prs:
            print("=" * 50)
            print("PULL REQUESTS")
            print("=" * 50)
            closed, failed = close_pull_requests(repo, confirm=True)
            total_closed += closed
            total_failed += failed
            print()
        
        # Summary
        print("=" * 50)
        print("SUMMARY")
        print("=" * 50)
        print(f"Total closed: {total_closed}")
        if total_failed > 0:
            print(f"Total failed: {total_failed}")
        
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
        description="Reset GitHub repository by closing issues and/or pull requests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python reset.py --issues                           # Close only issues
  python reset.py --prs                              # Close only PRs
  python reset.py --all                              # Close issues, PRs, and stop Devin sessions
  python reset.py --devin                            # Only stop Devin sessions
  python reset.py --all --repo owner/repo            # Specify repository
  
Environment Variables:
  GITHUB_TOKEN    GitHub personal access token (required)
  TARGET_REPO     Default repository in format "owner/repo"
  DEVIN_API_KEY   Devin API key (required if using --devin)
  DEVIN_ORG_ID    Devin organization ID (required if using --devin)
        """
    )
    
    parser.add_argument(
        "--repo",
        type=str,
        help='Repository in format "owner/repo" (e.g., "aniketm3/demo-targetIssues")'
    )
    
    parser.add_argument(
        "--issues",
        action="store_true",
        help="Close all open issues"
    )
    
    parser.add_argument(
        "--prs",
        action="store_true",
        help="Close all open pull requests"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Close both issues and pull requests"
    )
    
    parser.add_argument(
        "--devin",
        action="store_true",
        help="Stop all active Devin sessions"
    )
    
    args = parser.parse_args()
    
    # Validate that at least one action is specified
    if not (args.issues or args.prs or args.all or args.devin):
        parser.error("Must specify at least one action: --issues, --prs, --all, or --devin")
    
    # Get GitHub token from environment (only required if not just stopping Devin)
    github_token = None
    repo_name = None
    
    if args.issues or args.prs or args.all:
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
            print("  --repo flag: python reset.py --repo owner/repo")
            print("  TARGET_REPO env var: export TARGET_REPO='owner/repo'")
            exit(1)
        
        # Validate repository format
        if "/" not in repo_name:
            print(f"Error: Invalid repository format: {repo_name}")
            print('  Expected format: "owner/repo" (e.g., "aniketm3/demo-targetIssues")')
            exit(1)
        
        reset_repository(repo_name, github_token, args.issues, args.prs, args.all, args.devin)
    elif args.devin:
        # Just stop Devin sessions
        stop_devin_sessions()


if __name__ == "__main__":
    main()
