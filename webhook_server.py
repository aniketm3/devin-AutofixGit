#!/usr/bin/env python3
"""
GitHub webhook server to automatically handle issue and PR events.

Automated workflows:
1. PR opened by Devin → Updates issue labels: devin:in-progress → devin:awaiting-feedback
2. Human comments on 'needs-human-review' issue → Removes '✓ triaged' for re-triage
3. Human comments on 'devin:awaiting-feedback' issue → Removes labels for re-triage
4. Human comments on Devin PR → Updates linked issue to devin:queued for re-triage

Setup:
1. Run this server: python webhook_server.py
2. Expose it via ngrok or similar: ngrok http 5000
3. Add webhook in GitHub repo settings:
   - Payload URL: https://your-ngrok-url/webhook
   - Content type: application/json
   - Events: Issue comments, Pull requests, Pull request reviews, Pull request review comments
   - Secret: (optional, set WEBHOOK_SECRET in .env)

Usage:
    python webhook_server.py
    python webhook_server.py --port 8080
"""

import os
import hmac
import hashlib
import argparse
from flask import Flask, request, jsonify
from src.config import Config
from src.github_client import GitHubClient
from src.state_manager import StateManager

app = Flask(__name__)

# Global config (loaded on startup)
config = None
github_client = None
state_manager = None
webhook_secret = None


def verify_signature(payload_body, signature_header):
    """Verify that the webhook came from GitHub."""
    if not webhook_secret:
        return True  # Skip verification if no secret set
    
    if not signature_header:
        return False
    
    hash_object = hmac.new(
        webhook_secret.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    
    return hmac.compare_digest(expected_signature, signature_header)


def handle_pr_opened(payload):
    """Handle when a PR is opened - check if it's from Devin and update labels."""
    import re
    
    action = payload.get('action')
    
    # Only handle opened PRs
    if action != 'opened':
        return jsonify({'message': 'PR action ignored'}), 200
    
    pr = payload.get('pull_request', {})
    pr_number = pr.get('number')
    pr_body = pr.get('body', '')
    pr_user = pr.get('user', {}).get('login', '')
    
    # Try to find linked issue number in PR body
    issue_match = re.search(r'(?:fix|fixes|close|closes|resolve|resolves)\s+#(\d+)', pr_body, re.IGNORECASE)
    
    if not issue_match:
        return jsonify({'message': 'No linked issue found in PR'}), 200
    
    issue_number = int(issue_match.group(1))
    
    # Get the issue to check its labels
    try:
        issue = github_client.get_issue(issue_number)
        labels = [label.name for label in issue.labels]
        
        # Only handle if issue has devin:in-progress (meaning Devin is working on it)
        if 'devin:in-progress' not in labels:
            return jsonify({'message': 'Issue not from Devin workflow'}), 200
        
        # Update labels: devin:in-progress → devin:awaiting-feedback
        github_client.remove_labels(issue_number, ["devin:in-progress"])
        github_client.add_labels(issue_number, ["devin:awaiting-feedback"])
        
        # Post comment on issue
        comment = f"""## ✅ Devin completed this issue

Devin has analyzed and fixed this issue. A pull request has been created:

**PR**: {pr.get('html_url')}

Please review the changes and merge if appropriate.

---
*PR created by: {pr_user}*
"""
        github_client.create_comment(issue_number, comment)
        
        print(f"✓ PR #{pr_number} created for issue #{issue_number}")
        print(f"  Updated labels: devin:in-progress → devin:awaiting-feedback")
        
        return jsonify({
            'message': 'Labels updated',
            'issue_number': issue_number,
            'pr_number': pr_number
        }), 200
        
    except Exception as e:
        print(f"✗ Error handling PR opened: {e}")
        return jsonify({'error': str(e)}), 500


def handle_pr_feedback(payload, source="comment"):
    """Handle feedback on PRs (comments or reviews) - unified handler."""
    import re
    
    # Extract PR info based on source
    if source == "comment":
        # Comment on PR conversation (issue_comment event)
        issue = payload.get('issue', {})
        pr_number = issue.get('number')
        comment = payload.get('comment', {})
        comment_user = comment.get('user', {})
        
        # Get PR to find linked issue
        pr = github_client.repo.get_pull(pr_number)
        pr_body = pr.body or ''
    else:
        # PR review comment (pull_request_review_comment or pull_request_review event)
        pr = payload.get('pull_request', {})
        pr_number = pr.get('number')
        pr_body = pr.get('body', '')
        comment = payload.get('comment') or payload.get('review', {})
        comment_user = comment.get('user', {})
    
    print(f"[PR Feedback] Processing {source} on PR #{pr_number}")
    
    # Skip bot comments
    if comment_user.get('type') == 'Bot':
        print(f"[PR Feedback] Skipping bot comment")
        return jsonify({'message': 'Bot comment ignored'}), 200
    
    # Try to find linked issue number in PR body
    issue_match = re.search(r'(?:fix|fixes|close|closes|resolve|resolves)\s+#(\d+)', pr_body, re.IGNORECASE)
    
    if not issue_match:
        print(f"[PR Feedback] No linked issue found in PR body")
        return jsonify({'message': 'No linked issue found in PR'}), 200
    
    issue_number = int(issue_match.group(1))
    print(f"[PR Feedback] Found linked issue #{issue_number}")
    
    # Get the issue to check its labels
    try:
        linked_issue = github_client.get_issue(issue_number)
        labels = [label.name for label in linked_issue.labels]
        print(f"[PR Feedback] Issue #{issue_number} labels: {labels}")
        
        # Only handle if issue has devin:awaiting-feedback or devin:in-progress
        if 'devin:awaiting-feedback' not in labels and 'devin:in-progress' not in labels:
            print(f"[PR Feedback] Issue not in Devin workflow")
            return jsonify({'message': 'Issue not in Devin workflow'}), 200
        
        # Remove devin labels and ✓ triaged, add devin:queued
        labels_to_remove = ["✓ triaged"]
        if 'devin:awaiting-feedback' in labels:
            labels_to_remove.append("devin:awaiting-feedback")
        if 'devin:in-progress' in labels:
            labels_to_remove.append("devin:in-progress")
        
        github_client.remove_labels(issue_number, labels_to_remove)
        github_client.add_labels(issue_number, ["devin:queued"])
        
        # Clear the old Devin session from state so a new one can be created
        if state_manager and str(issue_number) in state_manager.state.get("devin_sessions", {}):
            del state_manager.state["devin_sessions"][str(issue_number)]
            state_manager.save()
            print(f"[PR Feedback] Cleared old Devin session for issue #{issue_number}")
        
        print(f"✓ PR #{pr_number} received feedback for issue #{issue_number}")
        print(f"  Comment by: {comment_user.get('login')}")
        print(f"  Updated labels to devin:queued")
        print(f"  Issue will be re-triaged and re-sent to Devin")
        
        return jsonify({
            'message': 'Labels updated for re-triage',
            'issue_number': issue_number,
            'pr_number': pr_number
        }), 200
        
    except Exception as e:
        print(f"✗ Error handling PR feedback: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle GitHub webhook events."""
    
    # Verify signature
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_signature(request.data, signature):
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Get event type
    event_type = request.headers.get('X-GitHub-Event')
    payload = request.json
    
    # Handle PR opened events
    if event_type == 'pull_request':
        return handle_pr_opened(payload)
    
    # Handle both issue comments and PR comments
    if event_type not in ['issue_comment', 'pull_request_review_comment', 'pull_request_review']:
        return jsonify({'message': 'Event ignored'}), 200
    
    action = payload.get('action')
    
    # Only handle new comments/reviews
    if action not in ['created', 'submitted']:
        return jsonify({'message': 'Action ignored'}), 200
    
    # Handle PR review comments
    if event_type in ['pull_request_review_comment', 'pull_request_review']:
        return handle_pr_feedback(payload, source="review")
    
    # Get issue and comment info (for issue comments)
    issue = payload.get('issue', {})
    comment = payload.get('comment', {})
    issue_number = issue.get('number')
    comment_user = comment.get('user', {})
    comment_body = comment.get('body', '')
    
    # Skip bot comments
    if comment_user.get('type') == 'Bot':
        return jsonify({'message': 'Bot comment ignored'}), 200
    
    # Skip automated triage comments (check for marker in comment body)
    if '## 🤖 Automated Triage Summary' in comment_body:
        return jsonify({'message': 'Automated triage comment ignored'}), 200
    
    # Skip automated Devin completion comments
    if '## ✅ Devin completed this issue' in comment_body:
        return jsonify({'message': 'Automated Devin comment ignored'}), 200
    
    # Check if this is a comment on a PR (issue will have pull_request field)
    if issue.get('pull_request'):
        return handle_pr_feedback(payload, source="comment")
    
    # Check if issue has labels that need re-triage on human comment
    labels = [label['name'] for label in issue.get('labels', [])]
    
    # Handle needs-human-review issues
    if 'needs-human-review' in labels:
        if '✓ triaged' not in labels:
            return jsonify({'message': 'Already unmarked for re-triage'}), 200
        
        # Remove '✓ triaged' label
        try:
            github_client.remove_labels(issue_number, ["✓ triaged"])
            
            print(f"✓ Removed '✓ triaged' from issue #{issue_number} (needs-human-review)")
            print(f"  Comment by: {comment_user.get('login')}")
            print(f"  Issue will be re-triaged on next orchestrator run")
            
            return jsonify({
                'message': 'Label removed',
                'issue_number': issue_number
            }), 200
            
        except Exception as e:
            print(f"✗ Error removing label from issue #{issue_number}: {e}")
            return jsonify({'error': str(e)}), 500
    
    # Handle devin:awaiting-feedback issues
    elif 'devin:awaiting-feedback' in labels:
        if '✓ triaged' not in labels:
            return jsonify({'message': 'Already unmarked for re-triage'}), 200
        
        # Remove '✓ triaged' and 'devin:awaiting-feedback', add devin:queued
        try:
            github_client.remove_labels(issue_number, ["✓ triaged", "devin:awaiting-feedback"])
            github_client.add_labels(issue_number, ["devin:queued"])
            
            # Clear the old Devin session from state so a new one can be created
            if state_manager and str(issue_number) in state_manager.state.get("devin_sessions", {}):
                del state_manager.state["devin_sessions"][str(issue_number)]
                state_manager.save()
                print(f"[Issue Comment] Cleared old Devin session for issue #{issue_number}")
            
            print(f"✓ Updated labels for issue #{issue_number}")
            print(f"  Comment by: {comment_user.get('login')}")
            print(f"  Labels: devin:awaiting-feedback → devin:queued")
            print(f"  Issue will be re-triaged and re-sent to Devin")
            
            return jsonify({
                'message': 'Labels updated for re-triage',
                'issue_number': issue_number
            }), 200
            
        except Exception as e:
            print(f"✗ Error updating labels for issue #{issue_number}: {e}")
            return jsonify({'error': str(e)}), 500
    
    else:
        return jsonify({'message': 'Not a retriageable issue'}), 200


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'}), 200


def main():
    global config, github_client, state_manager, webhook_secret
    
    parser = argparse.ArgumentParser(
        description="GitHub webhook server for issue comment events"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to run the webhook server on (default: 5000)"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    
    args = parser.parse_args()
    
    # Load config
    config = Config.from_env()
    github_client = GitHubClient(
        config.github_token,
        config.target_repo_owner,
        config.target_repo_name
    )
    state_manager = StateManager(config.state_file)
    webhook_secret = os.getenv("WEBHOOK_SECRET")
    
    print("=" * 50)
    print("GitHub Webhook Server")
    print("=" * 50)
    print(f"Target repo: {config.target_repo}")
    print(f"Listening on: http://{args.host}:{args.port}")
    print(f"Webhook URL: http://{args.host}:{args.port}/webhook")
    print(f"Health check: http://{args.host}:{args.port}/health")
    
    if webhook_secret:
        print("✓ Webhook signature verification enabled")
    else:
        print("⚠ Webhook signature verification disabled (set WEBHOOK_SECRET in .env)")
    
    print("\nTo expose this server publicly:")
    print(f"  ngrok http {args.port}")
    print("\nThen add the webhook in GitHub repo settings:")
    print("  Settings > Webhooks > Add webhook")
    print("  - Payload URL: https://your-ngrok-url/webhook")
    print("  - Content type: application/json")
    print("  - Events: Issue comments, Pull requests, Pull request reviews, Pull request review comments")
    print("=" * 50)
    print()
    
    # Run server
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
