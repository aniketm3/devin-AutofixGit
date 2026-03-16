"""
Issue triage engine using LLM for scoring and routing.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from github.Issue import Issue


@dataclass
class TriageResult:
    """Result of triaging an issue."""
    issue_number: int
    urgency_score: float
    fixability_score: float
    route: str  # "devin", "human", or "skip"
    reasoning: str
    triaged_at: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "issue_number": self.issue_number,
            "urgency_score": self.urgency_score,
            "fixability_score": self.fixability_score,
            "route": self.route,
            "reasoning": self.reasoning,
            "triaged_at": self.triaged_at,
        }


class TriageEngine:
    """Engine for triaging issues using LLM."""
    
    def __init__(self, provider: str, api_key: str, model: str):
        """
        Initialize triage engine.
        
        Args:
            provider: LLM provider ("openai" or "anthropic")
            api_key: API key for the LLM provider
            model: Model name (e.g., "gpt-4", "claude-3-5-sonnet-20241022")
        """
        self.provider = provider.lower()
        self.api_key = api_key
        self.model = model
        
        if self.provider != "openai":
            raise ValueError(f"Only OpenAI is supported. Got: {provider}")
        
        import openai
        self.client = openai.OpenAI(api_key=api_key)
    
    def analyze_issue(self, issue: Issue) -> TriageResult:
        """
        Analyze an issue and determine urgency, fixability, and routing.
        
        Args:
            issue: Issue to analyze
            
        Returns:
            TriageResult with scores and routing decision
        """
        prompt = self._build_prompt(issue)
        response = self._call_openai(prompt)
        
        # Parse LLM response
        try:
            result = json.loads(response)
            urgency = float(result["urgency_score"])
            fixability = float(result["fixability_score"])
            reasoning = result["reasoning"]
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Fallback to conservative scores if parsing fails
            urgency = 5.0
            fixability = 5.0
            reasoning = f"Failed to parse LLM response: {str(e)}"
        
        # Determine routing based on scores
        route = self._determine_route(urgency, fixability)
        
        return TriageResult(
            issue_number=issue.number,
            urgency_score=urgency,
            fixability_score=fixability,
            route=route,
            reasoning=reasoning,
            triaged_at=datetime.utcnow().isoformat(),
        )
    
    def _build_prompt(self, issue: Issue) -> str:
        """Build the prompt for LLM analysis."""
        # Handle timezone-aware datetime
        now = datetime.now(issue.created_at.tzinfo) if issue.created_at.tzinfo else datetime.utcnow()
        age_days = (now - issue.created_at).days
        labels = [label.name for label in issue.labels]
        author = issue.user.login if issue.user else "unknown"
        body = (issue.body or "")[:1000]
        
        return f"""You are analyzing a GitHub issue to determine if it can be autonomously fixed by an AI coding agent (Devin).

Issue: #{issue.number} - {issue.title}
Body: {body}
Labels: {', '.join(labels) if labels else 'None'}
Age: {age_days} days
Author: {author}

Analyze this issue and provide:
1. Urgency score (0-10): How critical is this issue?
   - High urgency (7-10): security issues, critical bugs, production blockers
   - Medium urgency (4-6): bugs, errors, broken functionality
   - Low urgency (0-3): features, enhancements, documentation

2. Fixability score (0-10): Can an AI agent fix this without human guidance?
   - High fixability (7-10): clear bug reports with reproduction steps, specific errors with stack traces
   - Medium fixability (4-6): feature requests with clear specs, bugs with some details
   - Low fixability (0-3): vague issues, architectural changes, requires design decisions

3. Brief reasoning (2-3 sentences)

Consider:
- Clear bug reports with reproduction steps = high fixability
- Vague feature requests or "redesign X" = low fixability
- Security issues or "critical" labels = high urgency
- Documentation or minor enhancements = low urgency

Respond ONLY with valid JSON in this exact format:
{{
    "urgency_score": <float between 0-10>,
    "fixability_score": <float between 0-10>,
    "reasoning": "<2-3 sentence explanation>"
}}"""
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert at analyzing GitHub issues. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content
    
    def _determine_route(self, urgency: float, fixability: float) -> str:
        """
        Determine routing based on scores.
        
        Args:
            urgency: Urgency score (0-10)
            fixability: Fixability score (0-10)
            
        Returns:
            Route: "devin", "human", or "skip"
        """
        if urgency >= 7 and fixability >= 7:
            return "devin"
        elif urgency >= 5 or fixability >= 5:
            return "human"
        else:
            return "skip"
