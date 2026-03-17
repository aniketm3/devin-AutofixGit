#!/usr/bin/env python3
"""
Check status of active Devin sessions and update GitHub with results.
"""

from src.config import Config
from src.github_client import GitHubClient
from src.devin_client import DevinClient
from src.state_manager import StateManager


def main():
    # Load config
    config = Config.from_env()
    
    # Initialize clients
    github = GitHubClient(config.github_token, config.target_repo_owner, config.target_repo_name)
    devin = DevinClient(config.devin_api_key, config.devin_org_id)
    state = StateManager(config.state_file)
    
    print("Checking Devin sessions...\n")
    
    # Get all issues with Devin sessions
    for issue_num_str, session_data in state.state.get("devin_sessions", {}).items():
        issue_num = int(issue_num_str)
        session_id = session_data["session_id"]
        
        print(f"Issue #{issue_num}:")
        print(f"  Session: {session_data['url']}")
        print(f"  Status: {session_data['status']}")
        
        # Check current status
        try:
            session = devin.get_session(session_id)
            
            # Update state
            state.store_devin_session(issue_num, session.to_dict())
            
            # Display PR info if exists
            if session.pull_requests:
                pr = session.pull_requests[0]
                print(f"  PR: {pr.pr_url}")
            
            # Check for errors or blocked status
            if session.status in ["error", "suspended"]:
                # Devin failed or got blocked
                print(f"  ✗ Session {session.status}: {session.status_detail}")
                
                comment = f"""## ⚠️ Devin encountered an issue

Devin was unable to complete this task automatically.

**Status**: {session.status}
**Detail**: {session.status_detail or 'Unknown'}

A human engineer should review this issue.

---
*Devin session: {session.url}*
"""
                github.create_comment(issue_num, comment)
                github.remove_labels(issue_num, ["devin:in-progress"])
                github.add_labels(issue_num, ["devin:blocked"])
                print("  Updated GitHub with blocked status")
            
            else:
                print(f"  Still running... ({session.status_detail or 'working'})")
        
        except Exception as e:
            print(f"  Error checking session: {e}")
        
        print()


if __name__ == "__main__":
    main()
