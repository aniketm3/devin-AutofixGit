#!/usr/bin/env python3
"""
Main orchestrator: Fetch issues → Triage with LLM → Label in GitHub
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
    
    # Initialize
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
        
        # Add GitHub labels
        label_map = {"devin": "needs-devin", "human": "needs-human-review", "skip": "not-suitable"}
        labels_to_add = [label_map[result.route], "✓ triaged"]
        github.add_labels(issue.number, labels_to_add)
        print(f"  Labeled: {', '.join(labels_to_add)}\n")


if __name__ == "__main__":
    main()
