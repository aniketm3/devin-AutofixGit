# Devin GitHub Issue Backlog Automation

Orchestration system that automatically triages GitHub issues and routes fixable ones to Devin for autonomous resolution.

## Overview

This system reads GitHub issues from a target repository, scores them for urgency and fixability, and automatically sends suitable issues to Devin for fixing. Results are reported back to GitHub with labels and PR links.

**Target Repository**: [aniketm3/demo-targetIssues](https://github.com/aniketm3/demo-targetIssues)

## Setup

### 1. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```bash
GITHUB_TOKEN=ghp_your_token_here
TARGET_REPO=aniketm3/demo-targetIssues
```

#### Creating a GitHub Token

1. Go to [GitHub Settings > Tokens](https://github.com/settings/tokens/new)
2. Create a new token with the following scopes:
   - `repo` (for private repos) or `public_repo` (for public repos only)
3. Copy the token and add it to your `.env` file

### 4. Load Environment Variables

```bash
source .env
# or
export $(cat .env | xargs)
```

## Usage

### Seed Demo Issues

Create test issues in the target repository:

```bash
# Create 7 demo issues (default)
python seed_issues.py

# Create specific number of issues
python seed_issues.py --count 5

# Specify repository explicitly
python seed_issues.py --count 10 --repo aniketm3/demo-targetIssues
```

The script creates issues with varying urgency and fixability scores:
- High urgency, high fixability: Login bugs, database errors
- Medium urgency: Input validation, documentation updates
- Low urgency, low fixability: Design tasks, feature requests

### Clear Issues

Close all open issues to reset the repository:

```bash
# Close all open issues
python clear_issues.py

# Specify repository explicitly
python clear_issues.py --repo aniketm3/demo-targetIssues
```

## Issue Templates

The seeding script includes 10 diverse issue templates:

1. **Login endpoint 500 error** - High urgency (9), High fixability (8)
2. **Input validation** - Medium urgency (6), High fixability (8)
3. **Database connection pool** - High urgency (8), Medium fixability (7)
4. **TypeError in pipeline** - High urgency (7), High fixability (9)
5. **Dark mode feature** - Low urgency (3), Low fixability (4)
6. **Homepage redesign** - Low urgency (4), Low fixability (2)
7. **API documentation** - Medium urgency (5), Medium fixability (7)
8. **Memory leak** - High urgency (9), Medium fixability (6)
9. **Rate limiting** - High urgency (7), High fixability (7)
10. **Mobile Safari bug** - Medium urgency (6), High fixability (8)

## Project Structure

```
devin-AutofixGit/
├── seed_issues.py          # Create demo issues
├── clear_issues.py         # Close all issues
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variable template
├── .env                   # Your credentials (gitignored)
└── README.md              # This file
```

## Next Steps

Future components to be implemented:
- `github_client.py` - GitHub API interface
- `triage.py` - Issue scoring and routing
- `devin_client.py` - Devin API interface
- `orchestrator.py` - Main automation pipeline
- `config.py` - Configuration management

## Troubleshooting

### "Error: GITHUB_TOKEN environment variable not set"

Make sure you've:
1. Created a `.env` file with your token
2. Loaded the environment variables: `source .env`

### "Error accessing repository"

Check that:
- The repository exists and you have access
- Your GitHub token has the correct scopes (`repo` or `public_repo`)
- The repository format is correct: `owner/repo`

### "Failed to create issue"

Verify that:
- You have write access to the repository
- The repository allows issue creation
- Your token hasn't expired
