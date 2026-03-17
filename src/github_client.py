"""
GitHub API client for fetching and updating issues.
"""

import warnings
from typing import List

warnings.filterwarnings('ignore', category=Warning)

from github import Github, GithubException, Auth
from github.Issue import Issue as GithubIssue


class Issue(GithubIssue):
    """Extended GitHub Issue with additional helper methods."""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "number": self.number,
            "title": self.title,
            "body": self.body or "",
            "labels": [label.name for label in self.labels],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "author": self.user.login if self.user else "unknown",
            "comments_count": self.comments,
            "url": self.html_url,
            "state": self.state,
        }


class GitHubClient:
    """Client for interacting with GitHub API."""
    
    def __init__(self, token: str, repo_owner: str, repo_name: str):
        """
        Initialize GitHub client.
        
        Args:
            token: GitHub personal access token
            repo_owner: Repository owner (e.g., "aniketm3")
            repo_name: Repository name (e.g., "demo-targetIssues")
        """
        auth = Auth.Token(token)
        self.github = Github(auth=auth)
        self.repo_name = f"{repo_owner}/{repo_name}"
        self.repo = self.github.get_repo(self.repo_name)
    
    def fetch_open_issues(self) -> List[GithubIssue]:
        """
        Fetch all open issues from the repository.
        
        Returns:
            List of GitHub Issue objects
        """
        try:
            issues = list(self.repo.get_issues(state='open'))
            return issues
        except GithubException as e:
            raise Exception(f"Failed to fetch issues: {e.data.get('message', str(e))}")
    
    def get_issue(self, issue_number: int) -> GithubIssue:
        """
        Get a specific issue by number.
        
        Args:
            issue_number: Issue number
            
        Returns:
            GitHub Issue object
        """
        try:
            issue = self.repo.get_issue(issue_number)
            return issue
        except GithubException as e:
            raise Exception(f"Failed to fetch issue #{issue_number}: {e.data.get('message', str(e))}")
    
    def create_comment(self, issue_number: int, body: str) -> None:
        """
        Create a comment on an issue.
        
        Args:
            issue_number: Issue number
            body: Comment text
        """
        try:
            issue = self.repo.get_issue(issue_number)
            issue.create_comment(body)
        except GithubException as e:
            raise Exception(f"Failed to create comment on issue #{issue_number}: {e.data.get('message', str(e))}")
    
    def add_labels(self, issue_number: int, labels: List[str]) -> None:
        """
        Add labels to an issue. Creates labels if they don't exist.
        
        Args:
            issue_number: Issue number
            labels: List of label names to add
        """
        try:
            # Ensure special labels exist with custom colors
            self._ensure_labels_exist(labels)
            
            issue = self.repo.get_issue(issue_number)
            issue.add_to_labels(*labels)
        except GithubException as e:
            raise Exception(f"Failed to add labels to issue #{issue_number}: {e.data.get('message', str(e))}")
    
    def _ensure_labels_exist(self, labels: List[str]) -> None:
        """Create labels if they don't exist, with custom colors."""
        label_colors = {
            "✓ triaged": "00FF00",  # Lime green
            "handled": "0366D6",  # Blue
            "awaiting-fix": "FFA500",  # Orange
            "needs-devin": "0E8A16",  # Dark green
            "needs-human-review": "FBCA04",  # Yellow
            "not-suitable": "D93F0B",  # Red
            "devin:queued": "EDEDED",  # Gray
            "devin:in-progress": "BFD4F2",  # Light blue
            "devin:awaiting-feedback": "FFA500",  # Orange
            "devin:blocked": "D93F0B",  # Red
            "devin:complete": "0E8A16",  # Dark green
        }
        
        existing_labels = {label.name for label in self.repo.get_labels()}
        
        for label_name in labels:
            if label_name not in existing_labels:
                color = label_colors.get(label_name, "EDEDED")  # Default gray
                try:
                    self.repo.create_label(label_name, color)
                except GithubException:
                    pass  # Label might have been created by another process
    
    def remove_labels(self, issue_number: int, labels: List[str]) -> None:
        """
        Remove labels from an issue.
        
        Args:
            issue_number: Issue number
            labels: List of label names to remove
        """
        try:
            issue = self.repo.get_issue(issue_number)
            for label in labels:
                try:
                    issue.remove_from_labels(label)
                except GithubException:
                    pass  # Label might not exist on the issue
        except GithubException as e:
            raise Exception(f"Failed to remove labels from issue #{issue_number}: {e.data.get('message', str(e))}")
    
    def close_issue(self, issue_number: int) -> None:
        """
        Close an issue.
        
        Args:
            issue_number: Issue number
        """
        try:
            issue = self.repo.get_issue(issue_number)
            issue.edit(state='closed')
        except GithubException as e:
            raise Exception(f"Failed to close issue #{issue_number}: {e.data.get('message', str(e))}")
