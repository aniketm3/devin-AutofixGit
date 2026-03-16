"""
State management for tracking processed issues and triage results.
"""

import json
import os
from typing import Dict, Optional


class StateManager:
    """Manages persistent state in a JSON file."""
    
    def __init__(self, state_file: str = "state.json"):
        """
        Initialize state manager.
        
        Args:
            state_file: Path to the state JSON file
        """
        self.state_file = state_file
        self.state = self._load_state()
    
    def _load_state(self) -> dict:
        """Load state from file or create empty state."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self._empty_state()
        return self._empty_state()
    
    def _empty_state(self) -> dict:
        """Create empty state structure."""
        return {
            "issues": {},
            "triage_results": {},
            "devin_sessions": {},
        }
    
    def save(self) -> None:
        """Save state to file."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def get_issue(self, issue_number: int) -> Optional[dict]:
        """Get stored issue data."""
        return self.state["issues"].get(str(issue_number))
    
    def store_issue(self, issue_number: int, issue_data: dict) -> None:
        """Store issue data."""
        self.state["issues"][str(issue_number)] = issue_data
        self.save()
    
    def get_triage_result(self, issue_number: int) -> Optional[dict]:
        """Get triage result for an issue."""
        return self.state["triage_results"].get(str(issue_number))
    
    def store_triage_result(self, issue_number: int, triage_data: dict) -> None:
        """Store triage result."""
        self.state["triage_results"][str(issue_number)] = triage_data
        self.save()
    
    def get_devin_session(self, issue_number: int) -> Optional[dict]:
        """Get Devin session data for an issue."""
        return self.state["devin_sessions"].get(str(issue_number))
    
    def store_devin_session(self, issue_number: int, session_data: dict) -> None:
        """Store Devin session data."""
        self.state["devin_sessions"][str(issue_number)] = session_data
        self.save()
    
    def is_issue_triaged(self, issue_number: int) -> bool:
        """Check if an issue has been triaged."""
        return str(issue_number) in self.state["triage_results"]
    
    def get_all_triage_results(self) -> Dict[str, dict]:
        """Get all triage results."""
        return self.state["triage_results"]
    
    def clear(self) -> None:
        """Clear all state."""
        self.state = self._empty_state()
        self.save()
