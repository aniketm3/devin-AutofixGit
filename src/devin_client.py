"""
Devin API client for creating and managing autonomous coding sessions.
"""

import time
import requests
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PullRequest:
    """Represents a pull request created by Devin."""
    pr_url: str
    pr_state: Optional[str]


@dataclass
class DevinSession:
    """Represents a Devin coding session."""
    session_id: str
    url: str
    status: str  # "new", "running", "exit", "error", "suspended"
    status_detail: Optional[str]  # "finished", "waiting_for_user", etc.
    pull_requests: List[PullRequest]
    created_at: int
    updated_at: int
    acus_consumed: float
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "url": self.url,
            "status": self.status,
            "status_detail": self.status_detail,
            "pull_requests": [{"pr_url": pr.pr_url, "pr_state": pr.pr_state} for pr in self.pull_requests],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "acus_consumed": self.acus_consumed,
        }


class DevinClient:
    """Client for interacting with Devin API."""
    
    def __init__(self, api_key: str, org_id: str):
        """
        Initialize Devin client.
        
        Args:
            api_key: Devin API key (starts with "cog_")
            org_id: Devin organization ID
        """
        self.api_key = api_key
        self.org_id = org_id
        self.base_url = "https://api.devin.ai/v3"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def create_session(self, issue_number: int, issue_title: str, issue_body: str, 
                      repo_url: str, issue_url: str) -> DevinSession:
        """
        Create a Devin session to fix a GitHub issue.
        
        Args:
            issue_number: GitHub issue number
            issue_title: Issue title
            issue_body: Issue description
            repo_url: Repository URL
            issue_url: Issue URL
            
        Returns:
            DevinSession object
        """
        prompt = self._build_prompt(issue_number, issue_title, issue_body, repo_url, issue_url)
        
        payload = {
            "prompt": prompt,
            "repos": [repo_url],
            "tags": ["github-automation", f"issue-{issue_number}"],
            "title": f"Fix issue #{issue_number}: {issue_title[:50]}"
        }
        
        response = requests.post(
            f"{self.base_url}/organizations/{self.org_id}/sessions",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        
        data = response.json()
        return self._parse_session(data)
    
    def get_session(self, session_id: str) -> DevinSession:
        """
        Get the current status of a Devin session.
        
        Args:
            session_id: Devin session ID
            
        Returns:
            DevinSession object with current status
        """
        # Devin API requires session ID to be prefixed with "devin-"
        devin_id = session_id if session_id.startswith("devin-") else f"devin-{session_id}"
        
        response = requests.get(
            f"{self.base_url}/organizations/{self.org_id}/sessions/{devin_id}",
            headers=self.headers
        )
        response.raise_for_status()
        
        data = response.json()
        return self._parse_session(data)
    
    def stop_session(self, session_id: str) -> bool:
        """
        Stop/cancel a running Devin session.
        
        Args:
            session_id: Devin session ID
            
        Returns:
            True if successfully stopped, False otherwise
        """
        # Devin API requires session ID to be prefixed with "devin-"
        devin_id = session_id if session_id.startswith("devin-") else f"devin-{session_id}"
        
        try:
            response = requests.post(
                f"{self.base_url}/organizations/{self.org_id}/sessions/{devin_id}/stop",
                headers=self.headers
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Failed to stop session {session_id}: {e}")
            return False
    
    def poll_until_complete(self, session_id: str, timeout: int = 1800, 
                           poll_interval: int = 30) -> DevinSession:
        """
        Poll a Devin session until it completes or times out.
        
        Args:
            session_id: Devin session ID
            timeout: Maximum time to wait in seconds (default 30 minutes)
            poll_interval: Time between polls in seconds (default 30 seconds)
            
        Returns:
            Final DevinSession object
        """
        start_time = time.time()
        
        while True:
            session = self.get_session(session_id)
            
            # Check if session is done
            if session.status in ["exit", "error", "suspended"]:
                return session
            
            # Check if finished successfully
            if session.status == "running" and session.status_detail == "finished":
                return session
            
            # Check timeout
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Session {session_id} did not complete within {timeout} seconds")
            
            # Wait before next poll
            time.sleep(poll_interval)
    
    def _build_prompt(self, issue_number: int, issue_title: str, issue_body: str,
                     repo_url: str, issue_url: str) -> str:
        """Build the prompt for Devin."""
        return f"""Fix GitHub issue #{issue_number} from {repo_url}

Title: {issue_title}

Description:
{issue_body}

Instructions:
1. Clone the repository
2. Analyze the issue and identify the root cause
3. Implement a fix
4. Run existing tests to verify the fix
5. Create a pull request with:
   - Clear description of the fix
   - Reference to issue #{issue_number}
   - Any relevant test results

Repository: {repo_url}
Issue URL: {issue_url}
"""
    
    def _parse_session(self, data: dict) -> DevinSession:
        """Parse API response into DevinSession object."""
        pull_requests = [
            PullRequest(pr_url=pr["pr_url"], pr_state=pr.get("pr_state"))
            for pr in data.get("pull_requests", [])
        ]
        
        return DevinSession(
            session_id=data["session_id"],
            url=data["url"],
            status=data["status"],
            status_detail=data.get("status_detail"),
            pull_requests=pull_requests,
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            acus_consumed=data["acus_consumed"]
        )
