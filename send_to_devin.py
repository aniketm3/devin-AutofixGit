#!/usr/bin/env python3
"""
Send issues labeled 'needs-devin' and 'awaiting-fix' to Devin for autonomous fixing.
"""

from src.config import Config
from src.github_client import GitHubClient
from src.devin_client import DevinClient
from src.state_manager import StateManager


def main():
    # Load config
    config = Config.from_env()
    
    if not config.devin_api_key or not config.devin_org_id:
        print("Error: Devin credentials not configured")
        print("Set DEVIN_API_KEY and DEVIN_ORG_ID in your .env file")
        return
    
    print(f"Target: {config.target_repo}\n")
    
    # Initialize clients
    github = GitHubClient(config.github_token, config.target_repo_owner, config.target_repo_name)
    devin = DevinClient(config.devin_api_key, config.devin_org_id)
    state = StateManager(config.state_file)
    
    # Fetch all open issues
    issues = github.fetch_open_issues()
    
    # Filter for issues that need Devin and haven't been fixed yet
    issues_to_fix = []
    for issue in issues:
        # Skip pull requests
        if issue.pull_request:
            continue
        
        labels = [label.name for label in issue.labels]
        if "needs-devin" in labels and "awaiting-fix-devin" in labels:
            issues_to_fix.append(issue)
    
    if not issues_to_fix:
        print("No issues found with 'needs-devin' and 'awaiting-fix-devin' labels")
        return
    
    print(f"Found {len(issues_to_fix)} issues to send to Devin\n")
    
    # Send each issue to Devin
    for issue in issues_to_fix:
        print(f"Issue #{issue.number}: {issue.title}")
        
        # Check if already sent to Devin
        existing_session = state.get_devin_session(issue.number)
        if existing_session:
            print(f"  Already sent to Devin: {existing_session['url']}")
            print()
            continue
        
        try:
            # Create Devin session
            repo_url = f"https://github.com/{config.target_repo}"
            session = devin.create_session(
                issue.number, issue.title, issue.body or "",
                repo_url, issue.html_url
            )
            
            # Store session in state
            state.store_devin_session(issue.number, session.to_dict())
            
            print(f"Created Devin session: {session.url}")
            
            # Update GitHub labels: remove awaiting-fix-devin, add devin-in-progress
            github.remove_labels(issue.number, ["awaiting-fix-devin"])
            github.add_labels(issue.number, ["devin-in-progress"])
            print(f"  Updated labels: awaiting-fix-devin → devin-in-progress")
            
        except Exception as e:
            print(f"Error: Failed to create Devin session: {e}")
        
        print()
    
    print("Done! Check progress with: python check_devin_sessions.py")


if __name__ == "__main__":
    main()
