# Devin GitHub Issue Backlog Automation

Orchestration system that automatically triages GitHub issues and routes fixable ones to Devin for autonomous resolution.

## Overview

This system reads GitHub issues from a target repository, scores them for urgency and fixability, and automatically sends suitable issues to Devin for fixing. Results are reported back to GitHub with labels and PR links.

**Target Repository**: [aniketm3/demo-targetIssues](https://github.com/aniketm3/demo-targetIssues)


### Step 1: Triage Issues

```bash
# Make sure environment variables are loaded
export $(grep -v '^#' .env | xargs)

# Run triage
python orchestrator.py
```

This will:
1. Fetch all open issues (skips PRs)
2. Score each with LLM (urgency + fixability)
3. Route and label:
   - **Devin route**: Labels `needs-devin`, `✓ triaged`, `devin:queued`
   - **Human route**: Labels `needs-human-review`, `✓ triaged` + posts summary comment
   - **Skip route**: Labels `not-suitable`, `✓ triaged`

### Step 2: Send to Devin

```bash
python send_to_devin.py
```

This will:
- Find all issues with `needs-devin` + `devin:queued` labels
- Create Devin sessions for each
- Update labels: `devin:queued` → `devin:in-progress`

### Step 3: Monitor Progress (Optional)

```bash
python check_devin_sessions.py
```

This displays:
- Current status of all Devin sessions
- PR links if created
- Handles `devin-blocked` status for errors

**Note**: With webhook enabled, you don't need to run this manually - labels update automatically when PRs are created.

### Step 4: Feedback Loop

**For `needs-human-review` issues:**
1. Comment on the issue in GitHub
2. Webhook removes `✓ triaged` automatically
3. Run `python orchestrator.py` to re-triage with feedback

**For Devin PRs:**
1. Comment on the PR in GitHub
2. Webhook removes `devin:awaiting-feedback` and `✓ triaged`, adds `devin:queued`
3. Webhook clears old Devin session
4. Run `python orchestrator.py` to re-triage
5. Run `python send_to_devin.py` to create new Devin session with feedback

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

### Webhook Setup (Recommended)

For automatic label management, set up the webhook server first:

```bash
# 1. Start the webhook server
python webhook_server.py --port 8080

# 2. In another terminal, expose it publicly
ngrok http 8080
```

Configure webhook in GitHub:
1. Go to your repo → Settings → Webhooks → Add webhook
2. Payload URL: `https://your-ngrok-url/webhook` (from ngrok output)
3. Content type: `application/json`
4. Events: Select these events:
   - **Issue comments** (for re-triage on feedback)
   - **Pull requests** (for automatic PR detection)
   - **Pull request reviews** (for PR feedback)
   - **Pull request review comments** (for PR feedback)
5. Add webhook

The webhook automatically handles:
- PR creation → Updates labels to `devin-awaiting-feedback`
- Comments on issues/PRs → Triggers re-triage
- Clears old Devin sessions when feedback is provided

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

### Reset Repository

Reset the repository by closing issues, PRs, and stopping Devin sessions:

```bash
# Complete reset (issues, PRs, and Devin sessions)
python reset.py --all

# Close only issues
python reset.py --issues

# Close only PRs
python reset.py --prs

# Stop only Devin sessions
python reset.py --devin

# Specify repository explicitly
python reset.py --all --repo aniketm3/demo-targetIssues
```

## Project Structure

```
devin-AutofixGit/
├── src/
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   ├── github_client.py       # GitHub API interface
│   ├── devin_client.py        # Devin API interface
│   ├── triage.py              # LLM-based issue scoring
│   └── state_manager.py       # State persistence
├── orchestrator.py            # Main automation pipeline
├── send_to_devin.py           # Send issues to Devin
├── check_devin_sessions.py    # Check Devin progress
├── webhook_server.py          # Webhook server for automatic comment detection
├── seed_issues.py             # Create demo issues
├── reset.py                   # Reset repository (issues/PRs/Devin)
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variable template
├── .env                      # Your credentials (gitignored)
├── state.json                # Runtime state (gitignored)
└── README.md                 # This file
```

## How It Works

### 1. Fetch & Triage
- GitHub client retrieves all open issues
- LLM analyzes each issue and scores:
  - **Urgency** (0-10): How critical is the issue?
  - **Fixability** (0-10): Can Devin fix it autonomously?

### 2. Route Based on Scores

**`needs-devin`** (High urgency + High fixability)
- Labels issue as `needs-devin`, `✓ triaged`, `awaiting-fix-devin`
- Run `send_to_devin.py` to actually send to Devin
- Devin attempts autonomous fix and creates PR
- Label flow:
  1. Initial: `awaiting-fix-devin`
  2. When sent to Devin: `devin-in-progress`
  3. When PR created: `devin-awaiting-user`
  4. User can comment on PR in GitHub, Devin automatically responds

**`needs-human-review`** (Medium scores)
- Generates summary with potential solutions
- Posts clarifying questions as GitHub comment
- Human reviews and decides next steps
- Labels: `needs-human-review`, `✓ triaged`
- After human comments, run `check_human_feedback.py` to remove `✓ triaged` for re-triage

**`not-suitable`** (Low scores)
- Just labels the issue
- No automated action taken
- Labels: `✓ triaged`, `not-suitable`

### 3. State Management
- Results saved to `state.json` to track triage results and Devin sessions
- GitHub labels are the source of truth for triage status
- Issues with `✓ triaged` label are skipped by the orchestrator

## Label Lifecycle

### Devin Route

| Stage | Labels | Trigger |
|-------|--------|---------|
| **Triaged** | `needs-devin`, `✓ triaged`, `devin:queued` | Orchestrator triages issue |
| **Working** | `needs-devin`, `✓ triaged`, `devin:in-progress` | send_to_devin.py creates session |
| **PR Created** | `needs-devin`, `✓ triaged`, `devin:awaiting-feedback` | Webhook detects PR opened |
| **Feedback Given** | `needs-devin`, `devin:queued` | Webhook detects comment on PR/issue |
| **Retriaged** | `needs-devin`, `✓ triaged`, `devin:queued` | Orchestrator re-triages |
| **Blocked** | `needs-devin`, `✓ triaged`, `devin:blocked` | Devin encounters error |

### Human Review Route

| Stage | Labels | Trigger |
|-------|--------|---------|
| **Triaged** | `needs-human-review`, `✓ triaged` | Orchestrator triages issue |
| **Feedback Given** | `needs-human-review` | Webhook detects comment |
| **Retriaged** | Varies based on new triage | Orchestrator re-triages |

### All Labels

- `✓ triaged` - Issue has been analyzed by the triage system
- `needs-devin` - Issue is suitable for Devin to fix
- `devin:queued` - Queued to be sent to Devin
- `devin:in-progress` - Devin is actively working on this issue
- `devin:awaiting-feedback` - Devin created a PR, waiting for human review
- `devin:blocked` - Devin encountered an error or got stuck
- `devin:complete` - Devin successfully fixed and PR was merged
- `needs-human-review` - Issue needs human review/clarification
- `not-suitable` - Issue not suitable for automation

## Webhook Setup (Optional)

For automatic detection of human comments on `needs-human-review` issues:

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the webhook server**:
   ```bash
   python webhook_server.py
   ```

3. **Expose it publicly** (GitHub needs to reach it):
   ```bash
   # Install ngrok: https://ngrok.com/download
   ngrok http 5000
   ```

4. **Configure webhook in GitHub**:
   - Go to your repo → Settings → Webhooks → Add webhook
   - Payload URL: `https://your-ngrok-url/webhook` (from ngrok output)
   - Content type: `application/json`
   - Events: Select "Issue comments"
   - Add webhook

5. **(Optional) Add webhook secret** for security:
   ```bash
   # In .env file
   WEBHOOK_SECRET=your_random_secret_here
   ```

Now when anyone comments on a `needs-human-review` issue, the webhook automatically removes the `✓ triaged` label so it gets re-triaged next time.

### Human Review Workflow

For issues labeled `needs-human-review`:
1. Issue gets both `needs-human-review` and `✓ triaged` labels
2. Human comments on the issue in GitHub (provides clarification, context, etc.)
3. **If webhook is running**: Automatically removes `✓ triaged` label
   **If no webhook**: Manually remove `✓ triaged` label in GitHub
4. Run `python orchestrator.py` to re-triage with the new context
5. Issue may be promoted to `needs-devin` if now suitable for Devin
6. Or it stays as `needs-human-review` if still needs human work

## Complete Workflow Example

```bash
# 1. Start webhook server (recommended for automation)
python webhook_server.py --port 8080  # In terminal 1
ngrok http 8080                        # In terminal 2, then configure GitHub webhook

# 2. Seed test issues
python seed_issues.py --count 5

# 3. Triage issues
python orchestrator.py

# 4. Send issues to Devin
python send_to_devin.py

# 5. (Optional) Monitor Devin progress
python check_devin_sessions.py

# When Devin creates a PR:
# - Webhook automatically updates labels to devin-awaiting-feedback
# - Review the PR on GitHub

# If you want changes to the PR:
# - Comment on the PR in GitHub
# - Webhook automatically updates labels and clears old session
# - Re-run orchestrator and send_to_devin:
python orchestrator.py
python send_to_devin.py

# For needs-human-review issues:
# - Comment on the issue in GitHub
# - Webhook automatically removes ✓ triaged
# - Re-run orchestrator to re-triage:
python orchestrator.py
```
