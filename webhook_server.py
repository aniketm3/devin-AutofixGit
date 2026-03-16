#!/usr/bin/env python3
"""
GitHub webhook server to automatically handle issue comments.

When a human comments on a 'needs-human-review' issue, this webhook:
1. Receives the event from GitHub
2. Removes the '✓ triaged' label
3. Issue will be re-triaged on next orchestrator run

Setup:
1. Run this server: python webhook_server.py
2. Expose it via ngrok or similar: ngrok http 5000
3. Add webhook in GitHub repo settings:
   - Payload URL: https://your-ngrok-url/webhook
   - Content type: application/json
   - Events: Issue comments
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

app = Flask(__name__)

# Global config (loaded on startup)
config = None
github_client = None
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


@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle GitHub webhook events."""
    
    # Verify signature
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_signature(request.data, signature):
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Get event type
    event_type = request.headers.get('X-GitHub-Event')
    
    if event_type != 'issue_comment':
        return jsonify({'message': 'Event ignored'}), 200
    
    payload = request.json
    action = payload.get('action')
    
    # Only handle new comments
    if action != 'created':
        return jsonify({'message': 'Action ignored'}), 200
    
    # Get issue and comment info
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
    
    # Handle devin-awaiting-feedback issues
    elif 'devin-awaiting-feedback' in labels:
        if '✓ triaged' not in labels:
            return jsonify({'message': 'Already unmarked for re-triage'}), 200
        
        # Remove '✓ triaged' and 'devin-awaiting-feedback' labels
        try:
            github_client.remove_labels(issue_number, ["✓ triaged", "devin-awaiting-feedback"])
            
            print(f"✓ Removed '✓ triaged' and 'devin-awaiting-feedback' from issue #{issue_number}")
            print(f"  Comment by: {comment_user.get('login')}")
            print(f"  Issue will be re-triaged on next orchestrator run")
            
            return jsonify({
                'message': 'Labels removed',
                'issue_number': issue_number
            }), 200
            
        except Exception as e:
            print(f"✗ Error removing labels from issue #{issue_number}: {e}")
            return jsonify({'error': str(e)}), 500
    
    else:
        return jsonify({'message': 'Not a retriageable issue'}), 200


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'}), 200


def main():
    global config, github_client, webhook_secret
    
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
    print("  - Events: Issue comments")
    print("=" * 50)
    print()
    
    # Run server
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
