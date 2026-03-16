#!/usr/bin/env python3
"""
Seed demo issues into a GitHub repository for testing the Devin automation system.

Usage:
    python seed_issues.py --count 7
    python seed_issues.py --count 10 --repo owner/repo
"""

import os
import argparse
import warnings
from typing import List, Dict

# Suppress SSL warnings on macOS (must be before imports)
warnings.filterwarnings('ignore', category=Warning)

from github import Github, GithubException, Auth


# Issue templates with varying urgency and fixability
ISSUE_TEMPLATES = [
    {
        "title": "Login endpoint returns 500 error on valid credentials",
        "body": """## Description
The `/api/auth/login` endpoint is returning a 500 Internal Server Error when users submit valid credentials.

## Steps to Reproduce
1. Send POST request to `/api/auth/login`
2. Include valid username and password in request body
3. Observe 500 error response

## Expected Behavior
Should return 200 OK with authentication token

## Actual Behavior
Returns 500 Internal Server Error

## Error Log
```
TypeError: Cannot read property 'id' of undefined
    at AuthController.login (auth.controller.js:45)
```

## Environment
- Node.js v18.0.0
- Express v4.18.0

## Priority
High - blocking user authentication""",
        "labels": ["bug", "critical", "backend"],
        "urgency": 9,
        "fixability": 8,
    },
    {
        "title": "Add input validation to user registration form",
        "body": """## Description
The user registration form currently accepts invalid email formats and weak passwords.

## Requirements
- Email validation (RFC 5322 compliant)
- Password requirements:
  - Minimum 8 characters
  - At least one uppercase letter
  - At least one number
  - At least one special character
- Display helpful error messages

## Acceptance Criteria
- [ ] Email validation implemented
- [ ] Password strength validation implemented
- [ ] Error messages display correctly
- [ ] Tests added for validation logic

## Files to Modify
- `src/components/RegistrationForm.tsx`
- `src/utils/validation.ts`""",
        "labels": ["enhancement", "frontend", "security"],
        "urgency": 6,
        "fixability": 8,
    },
    {
        "title": "Database connection pool exhausted under load",
        "body": """## Description
Application crashes with "connection pool exhausted" error when handling more than 50 concurrent requests.

## Error Message
```
Error: Connection pool exhausted - unable to acquire connection
    at Pool.acquire (pool.js:234)
    at Database.query (database.js:89)
```

## Current Configuration
```javascript
const pool = new Pool({
  max: 10,
  idleTimeoutMillis: 30000
});
```

## Expected Fix
Increase pool size and implement proper connection cleanup

## Impact
High - causes production outages during peak traffic""",
        "labels": ["bug", "performance", "database"],
        "urgency": 8,
        "fixability": 7,
    },
    {
        "title": "TypeError in data processing pipeline",
        "body": """## Bug Report

Getting a TypeError when processing CSV uploads.

## Stack Trace
```python
Traceback (most recent call last):
  File "pipeline.py", line 67, in process_data
    result = transform(row['amount'])
TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'
```

## Code Location
`src/pipeline.py` line 67

## How to Reproduce
1. Upload CSV with missing 'amount' field
2. Run data processing job
3. Error occurs

## Suggested Fix
Add null check before arithmetic operations""",
        "labels": ["bug", "data-processing"],
        "urgency": 7,
        "fixability": 9,
    },
    {
        "title": "Add dark mode support to application",
        "body": """## Feature Request

Add dark mode theme support across the entire application.

## Requirements
- Toggle button in settings
- Persist user preference
- Apply theme to all pages
- Smooth transition animation

## Design
Mockups available in Figma (link TBD)

## Technical Considerations
- CSS variables for theming
- LocalStorage for persistence
- Consider system preference detection

## Priority
Low - nice to have feature""",
        "labels": ["enhancement", "ui", "feature-request"],
        "urgency": 3,
        "fixability": 4,
    },
    {
        "title": "Redesign homepage layout and navigation",
        "body": """## Design Task

The current homepage needs a complete redesign to improve user experience and modernize the look.

## Goals
- More intuitive navigation
- Better visual hierarchy
- Mobile-responsive design
- Improved accessibility

## Scope
This is a large project requiring:
- UX research
- Design mockups
- Stakeholder approval
- Multiple iterations

## Timeline
Estimated 2-3 sprints

## Notes
Requires collaboration with design team and product management.""",
        "labels": ["design", "enhancement", "needs-discussion"],
        "urgency": 4,
        "fixability": 2,
    },
    {
        "title": "Update API documentation for v2 endpoints",
        "body": """## Documentation Task

API documentation is outdated and missing information about v2 endpoints.

## What Needs Updating
- Authentication flow changes
- New endpoints added in v2
- Deprecated endpoints
- Example requests/responses

## Files
- `docs/api/authentication.md`
- `docs/api/endpoints.md`
- `docs/api/examples.md`

## Priority
Medium - developers are asking questions about undocumented features""",
        "labels": ["documentation"],
        "urgency": 5,
        "fixability": 7,
    },
    {
        "title": "Memory leak in WebSocket connection handler",
        "body": """## Bug Report

Memory usage continuously increases when WebSocket connections are active, eventually causing OOM crashes.

## Symptoms
- Memory usage grows ~50MB per hour
- Garbage collection doesn't reclaim memory
- Server crashes after 8-12 hours

## Profiling Data
Heap snapshot shows event listeners not being cleaned up properly.

## Suspected Cause
WebSocket event handlers not removed on disconnect

## Code Location
`src/websocket/handler.js`

## Reproduction
1. Start server
2. Connect 10+ WebSocket clients
3. Monitor memory usage over 2 hours
4. Observe continuous growth

## Impact
Critical - requires daily server restarts in production""",
        "labels": ["bug", "critical", "memory-leak", "websocket"],
        "urgency": 9,
        "fixability": 6,
    },
    {
        "title": "Implement rate limiting for API endpoints",
        "body": """## Security Enhancement

Add rate limiting to prevent API abuse and DDoS attacks.

## Requirements
- 100 requests per minute per IP
- 1000 requests per hour per API key
- Return 429 status code when limit exceeded
- Include rate limit headers in response

## Implementation Suggestions
- Use Redis for distributed rate limiting
- Middleware approach for easy integration
- Configurable limits per endpoint

## Endpoints to Protect
- `/api/auth/*`
- `/api/data/*`
- `/api/search`

## Testing
- Unit tests for rate limiter
- Load testing to verify limits""",
        "labels": ["security", "enhancement", "backend"],
        "urgency": 7,
        "fixability": 7,
    },
    {
        "title": "Fix broken image uploads on mobile Safari",
        "body": """## Bug Report

Image uploads fail on mobile Safari (iOS 15+) but work on other browsers.

## Steps to Reproduce
1. Open app on iPhone with Safari
2. Navigate to profile settings
3. Tap "Upload Photo"
4. Select image from photo library
5. Upload fails with no error message

## Expected
Image should upload successfully

## Actual
Upload silently fails, no feedback to user

## Browser Info
- Safari on iOS 15.0+
- Works on Chrome iOS
- Works on desktop Safari

## Console Errors
```
Failed to load resource: the server responded with a status of 400
```

## Suspected Issue
MIME type or CORS issue specific to mobile Safari""",
        "labels": ["bug", "mobile", "frontend"],
        "urgency": 6,
        "fixability": 8,
    },
]


def create_issues(repo_name: str, count: int, github_token: str) -> None:
    """
    Create demo issues in the specified repository.
    
    Args:
        repo_name: Repository in format "owner/repo"
        count: Number of issues to create
        github_token: GitHub personal access token
    """
    try:
        # Initialize GitHub client
        auth = Auth.Token(github_token)
        g = Github(auth=auth)
        repo = g.get_repo(repo_name)
        
        print(f"Target repository: {repo_name}")
        print(f"Creating {count} demo issues...\n")
        
        # Create issues from templates
        issues_to_create = ISSUE_TEMPLATES[:count]
        created_issues = []
        
        for i, template in enumerate(issues_to_create, 1):
            try:
                issue = repo.create_issue(
                    title=template["title"],
                    body=template["body"],
                    labels=template["labels"]
                )
                created_issues.append(issue)
                print(f"[{i}/{count}] Created issue #{issue.number}: {template['title']}")
                print(f"  Urgency: {template['urgency']}/10, Fixability: {template['fixability']}/10")
                print(f"  URL: {issue.html_url}\n")
                
            except GithubException as e:
                print(f"Failed to create issue: {template['title']}")
                print(f"  Error: {e.data.get('message', str(e))}\n")
        
        print(f"\nSuccessfully created {len(created_issues)} issues")
        print(f"Issue distribution:")
        print(f"  High urgency (7-10): {sum(1 for t in issues_to_create if t['urgency'] >= 7)}")
        print(f"  High fixability (7-10): {sum(1 for t in issues_to_create if t['fixability'] >= 7)}")
        
    except GithubException as e:
        print(f"Error accessing repository: {e.data.get('message', str(e))}")
        print("\nPossible issues:")
        print("  - Repository doesn't exist or is private")
        print("  - GitHub token doesn't have 'repo' or 'public_repo' scope")
        print("  - Token doesn't have write access to the repository")
        exit(1)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Seed demo issues into a GitHub repository for testing Devin automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python seed_issues.py --count 7
  python seed_issues.py --count 10 --repo aniketm3/demo-targetIssues
  
Environment Variables:
  GITHUB_TOKEN    GitHub personal access token (required)
  TARGET_REPO     Default repository in format "owner/repo"
        """
    )
    
    parser.add_argument(
        "--count",
        type=int,
        default=7,
        choices=range(1, len(ISSUE_TEMPLATES) + 1),
        help=f"Number of issues to create (1-{len(ISSUE_TEMPLATES)})"
    )
    
    parser.add_argument(
        "--repo",
        type=str,
        help='Repository in format "owner/repo" (e.g., "aniketm3/demo-targetIssues")'
    )
    
    args = parser.parse_args()
    
    # Get GitHub token from environment
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable not set")
        print("\nTo fix this:")
        print("  1. Create a GitHub Personal Access Token at:")
        print("     https://github.com/settings/tokens/new")
        print("  2. Grant 'repo' or 'public_repo' scope")
        print("  3. Export the token: export GITHUB_TOKEN='your_token_here'")
        exit(1)
    
    # Get repository name
    repo_name = args.repo or os.getenv("TARGET_REPO")
    if not repo_name:
        print("Error: Repository not specified")
        print("\nProvide repository using either:")
        print("  --repo flag: python seed_issues.py --repo owner/repo")
        print("  TARGET_REPO env var: export TARGET_REPO='owner/repo'")
        exit(1)
    
    # Validate repository format
    if "/" not in repo_name:
        print(f"Error: Invalid repository format: {repo_name}")
        print('  Expected format: "owner/repo" (e.g., "aniketm3/demo-targetIssues")')
        exit(1)
    
    create_issues(repo_name, args.count, github_token)


if __name__ == "__main__":
    main()
