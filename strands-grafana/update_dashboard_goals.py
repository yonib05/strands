#!/usr/bin/env python3
"""
Update Grafana dashboard goal lines with labels from the database.
Run after `cargo run -- load-goals` to sync labels to the dashboard.

Usage:
    python3 update_dashboard_goals.py
"""

import json
import sqlite3
import os

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "..", "metrics.db")
DASHBOARD_PATH = os.path.join(SCRIPT_DIR, "provisioning/dashboards/health.json")

# Panel ID to goal metric mapping
PANEL_GOAL_MAPPING = {
    13: "ci_failure_rate_percent",      # CI Failure Rate
    15: "pr_acceptance_rate_min",       # PR Acceptance Rate
    18: "community_share_percent_min",  # Community PR Share
    22: "contributor_retention_min",    # Contributor Retention
    7:  "time_to_first_response_hours", # Time to First Response
    17: "cycle_time_hours",             # Cycle Time
    20: "time_to_first_review_hours",   # Time to First Review
}

def load_goals_from_db():
    """Load goals with labels from SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT metric, value, label FROM goals")
    goals = {row[0]: {"value": row[1], "label": row[2] or "Goal"} for row in cursor.fetchall()}
    conn.close()
    return goals

def update_dashboard(goals):
    """Update dashboard JSON with goal labels."""
    with open(DASHBOARD_PATH) as f:
        dashboard = json.load(f)

    updated = []

    for panel in dashboard['panels']:
        panel_id = panel.get('id')

        if panel_id not in PANEL_GOAL_MAPPING:
            continue

        metric = PANEL_GOAL_MAPPING[panel_id]
        if metric not in goals:
            continue

        goal = goals[metric]
        label = goal['label']

        # Update query alias in targets
        if 'targets' in panel:
            for target in panel['targets']:
                if target.get('refId') == 'Goal':
                    for field in ['queryText', 'rawQueryText']:
                        if field in target:
                            # Replace the alias in the query
                            import re
                            target[field] = re.sub(
                                r'as "Goal[^"]*"',
                                f'as "{label}"',
                                target[field]
                            )

        # Update field overrides matcher
        if 'fieldConfig' in panel and 'overrides' in panel['fieldConfig']:
            for override in panel['fieldConfig']['overrides']:
                matcher = override.get('matcher', {})
                if matcher.get('id') == 'byName' and 'Goal' in matcher.get('options', ''):
                    matcher['options'] = label

        updated.append(f"{panel.get('title', 'Unknown')} -> {label}")

    with open(DASHBOARD_PATH, 'w') as f:
        json.dump(dashboard, f, indent=2)

    return updated

def main():
    print("Loading goals from database...")
    goals = load_goals_from_db()
    print(f"Found {len(goals)} goals:\n")

    for metric, goal in sorted(goals.items()):
        print(f"  {metric}: {goal['value']} ({goal['label']})")

    print("\nUpdating dashboard...")
    updated = update_dashboard(goals)

    print(f"\nUpdated {len(updated)} panels:")
    for u in updated:
        print(f"  - {u}")

    print("\nDone! Restart Grafana to see changes:")
    print("  docker-compose restart")

if __name__ == "__main__":
    main()
