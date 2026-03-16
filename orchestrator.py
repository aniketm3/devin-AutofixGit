#!/usr/bin/env python3
"""
Triage orchestrator: Fetch → Triage → Route → Label
Does NOT automatically call Devin. Use send_to_devin.py for that.
"""

import sys
from src.config import Config
from src.github_client import GitHubClient
from src.triage import TriageEngine
from src.state_manager import StateManager


def main():
    # Load config
    config = Config.from_env()
    print(f"Target: {config.target_repo}\n")
    
    # Initialize clients
    github = GitHubClient(config.github_token, config.target_repo_owner, config.target_repo_name)
    triage = TriageEngine("openai", config.llm_api_key, config.llm_model)
    state = StateManager(config.state_file)
    
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
            # Label for Devin but don't call it yet
            labels = ["needs-devin", "✓ triaged", "awaiting-fix-devin"]
            github.add_labels(issue.number, labels)
            print("  Labeled: needs-devin, awaiting-fix-devin")
        
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
    
    print("\nTriage complete!")
    print("To send 'needs-devin' issues to Devin, run: python send_to_devin.py")


if __name__ == "__main__":
    main()
