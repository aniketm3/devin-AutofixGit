#!/usr/bin/env python3
"""
Main orchestrator: Fetch → Triage → Route (Devin/Human/Skip)
"""

import sys
from src.config import Config
from src.github_client import GitHubClient
from src.triage import TriageEngine
from src.state_manager import StateManager
from src.devin_client import DevinClient


def main():
    # Load config
    config = Config.from_env()
    print(f"Target: {config.target_repo}\n")
    
    # Initialize clients
    github = GitHubClient(config.github_token, config.target_repo_owner, config.target_repo_name)
    triage = TriageEngine("openai", config.llm_api_key, config.llm_model)
    state = StateManager(config.state_file)
    
    # Initialize Devin client if credentials available
    devin = None
    if config.devin_api_key and config.devin_org_id:
        devin = DevinClient(config.devin_api_key, config.devin_org_id)
    
    # Fetch issues
    issues = github.fetch_open_issues()
    print(f"Found {len(issues)} open issues\n")
    
    # Process each issue
    for issue in issues:
        print(f"Issue #{issue.number}: {issue.title}")
        
        # Skip if already triaged
        if state.is_issue_triaged(issue.number):
            print("  Already triaged\n")
            continue
        
        # Triage with LLM
        result = triage.analyze_issue(issue)
        state.store_triage_result(issue.number, result.to_dict())
        
        print(f"  Urgency: {result.urgency_score:.1f}, Fixability: {result.fixability_score:.1f}")
        print(f"  Route: {result.route}")
        
        # Handle routing
        if result.route == "devin":
            # Send to Devin
            label_map = {"devin": "needs-devin", "human": "needs-human-review", "skip": "not-suitable"}
            labels = [label_map[result.route], "✓ triaged"]
            github.add_labels(issue.number, labels)
            
            if devin:
                try:
                    repo_url = f"https://github.com/{config.target_repo}"
                    session = devin.create_session(
                        issue.number, issue.title, issue.body or "",
                        repo_url, issue.html_url
                    )
                    state.store_devin_session(issue.number, session.to_dict())
                    print(f"  Created Devin session: {session.url}")
                    github.add_labels(issue.number, ["devin-in-progress"])
                except Exception as e:
                    print(f"  Failed to create Devin session: {e}")
            else:
                print("  Devin credentials not configured - skipping automation")
        
        elif result.route == "human":
            # Generate summary and questions
            labels = ["needs-human-review", "✓ triaged"]
            github.add_labels(issue.number, labels)
            
            print("  Generating review summary...")
            summary = triage.generate_human_review_summary(issue)
            comment = f"""## 🤖 Automated Triage Summary

{summary}

---
*This summary was generated automatically. A human should review this issue.*
"""
            github.create_comment(issue.number, comment)
            print("  Posted review summary as comment")
        
        else:  # skip
            # Just label, no action
            labels = ["not-suitable", "✓ triaged"]
            github.add_labels(issue.number, labels)
            print("  Skipped (not suitable for automation)")
        
        print()


if __name__ == "__main__":
    main()
