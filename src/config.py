"""
Configuration management for the Devin automation system.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Configuration for the Devin automation system."""
    
    # GitHub
    github_token: str
    target_repo_owner: str
    target_repo_name: str
    
    # Devin (optional for now)
    devin_api_key: Optional[str] = None
    devin_org_id: Optional[str] = None
    
    # LLM for triage
    llm_api_key: Optional[str] = None
    llm_model: str = "gpt-4"
    
    # Orchestration
    state_file: str = "state.json"
    poll_interval: int = 30
    session_timeout: int = 1800
    
    @property
    def target_repo(self) -> str:
        """Get the full repository name in owner/repo format."""
        return f"{self.target_repo_owner}/{self.target_repo_name}"
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        target_repo = os.getenv("TARGET_REPO", "")
        
        if not target_repo or "/" not in target_repo:
            raise ValueError(
                "TARGET_REPO must be set in format 'owner/repo' "
                "(e.g., 'aniketm3/demo-targetIssues')"
            )
        
        owner, repo = target_repo.split("/", 1)
        
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            raise ValueError("GITHUB_TOKEN environment variable is required")
        
        llm_api_key = os.getenv("LLM_API_KEY")
        if not llm_api_key:
            raise ValueError("LLM_API_KEY environment variable is required for triage")
        
        return cls(
            github_token=github_token,
            target_repo_owner=owner,
            target_repo_name=repo,
            devin_api_key=os.getenv("DEVIN_API_KEY"),
            devin_org_id=os.getenv("DEVIN_ORG_ID"),
            llm_api_key=llm_api_key,
            llm_model=os.getenv("LLM_MODEL", "gpt-4"),
            state_file=os.getenv("STATE_FILE", "state.json"),
            poll_interval=int(os.getenv("POLL_INTERVAL", "30")),
            session_timeout=int(os.getenv("SESSION_TIMEOUT", "1800")),
        )
