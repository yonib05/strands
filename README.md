# Strands Personal Monorepo

Personal monorepo for Strands projects. To later be moved into the strands-labs org.

## Repository Structure

### strands-metrics/

Rust CLI tool for syncing GitHub organization data and package download stats to SQLite. Collects issues, pull requests, commits, stars, CI workflow runs, and download metrics from PyPI/npm. Computes daily aggregated metrics per repository.

### strands-grafana/

Grafana configuration with SQLite datasource for visualizing GitHub metrics. Includes:
- **Health Dashboard** - DORA-style metrics with goal lines for tracking targets
- **Team Dashboard** - Team performance scorecard and review balance
- **Triage Dashboard** - Operational views for daily/weekly triage
- **Adoption Section** - Package download trends from PyPI and npm

Configuration files:
- `goals.yaml` - Configurable goal thresholds for dashboard alerts
- `packages.yaml` - Package-to-repo mappings for download tracking

### strands-rs/

Experimental Strands SDK implementation in Rust.

### filament-sys/

Rust FFI bindings for the Filament specification. Filament is a specification for autonomous AI agents with deterministic execution, WebAssembly sandboxing, and resource limits.

### metrics.db

SQLite database tracked via Git LFS. Contains synced GitHub metrics, package downloads, and pre-computed daily aggregates.

## Prerequisites for Grafana

### Git LFS

Required to clone the metrics.db file. Install and initialize:

```bash
# macOS
brew install git-lfs

# Ubuntu/Debian
sudo apt-get install git-lfs

# Initialize
git lfs install
git lfs pull
```

Verify with `git lfs ls-files` - should show metrics.db.

### Other

- Docker and Docker Compose (Or `podman` which I prefer)

## Quick Start

```bash
# Clone and setup Git LFS
git clone <repo-url>
cd strands-personal-mono
git lfs install
git lfs pull

# Launch Grafana
cd strands-grafana
docker-compose up # or podman compose up
# Navigate to http://localhost:3000
```

## CLI Commands

The `strands-metrics` CLI provides several commands for managing metrics data:

### GitHub Data Sync

```bash
# Sync GitHub data (requires GITHUB_TOKEN)
export GITHUB_TOKEN="your_token"
cargo run --release -- sync

# Garbage collection - marks deleted items
cargo run --release -- sweep
```

### Package Download Stats

```bash
# Sync recent download stats (default: 30 days)
cargo run --release -- sync-downloads

# Sync with custom day range
cargo run --release -- sync-downloads --days 7

# Backfill historical data (PyPI: 180 days, npm: 365 days)
cargo run --release -- backfill-downloads
```

Download stats are fetched from:
- **PyPI** (pypistats.org) - Updated daily ~01:00 UTC, 180 days retention
- **npm** (api.npmjs.org) - Updated daily, 365+ days retention

Note: Data has ~24h delay due to upstream API update schedules.

### Goals Management

```bash
# Load goals from config into database
cargo run --release -- load-goals

# List all configured goals
cargo run --release -- list-goals
```

Goals appear as threshold lines on dashboard charts. Edit `strands-grafana/goals.yaml` to adjust targets.

### Raw SQL Queries

```bash
# Run arbitrary SQL against the database
cargo run --release -- query "SELECT * FROM daily_metrics LIMIT 5"
```

## Configuration Files

### strands-grafana/goals.yaml

Defines goal thresholds for rate/time-based metrics. Each goal can include an optional label for dashboard display:

```yaml
goals:
  # Simple format (value only)
  avg_merge_time_hours: 24

  # Extended format with custom label
  cycle_time_hours:
    value: 336
    label: "Goal (14d)"

  time_to_first_review_hours:
    value: 72
    label: "Goal (72h)"

  ci_failure_rate_percent:
    value: 30
    label: "Goal (30%)"
```

After updating goals, run `load-goals` to sync to the database. The `update_dashboard_goals.py` script can update dashboard panel labels to match.

### strands-grafana/packages.yaml

Maps GitHub repos to published packages for download tracking:

```yaml
repo_mappings:
  sdk-python:
    - package: strands-agents
      registry: pypi
  sdk-typescript:
    - package: "@strands-agents/sdk"
      registry: npm
```

## GitHub Action (Automated Updates)

The repository includes a GitHub Action that runs daily at 6 AM UTC to sync all metrics.

### Required Secret

Create a repository secret named `METRICS_PAT` containing a GitHub Personal Access Token with:
- `repo` scope (for accessing repository data)
- `read:org` scope (for organization membership)

### Workflow

The action (`.github/workflows/metrics.yaml`) runs:
1. `sync` - Incrementally fetches new issues, PRs, commits, stars, and CI runs
2. `sweep` - Garbage collection to mark deleted items
3. `sync-downloads` - Fetches package download stats from PyPI and npm
4. Commits and pushes updated `metrics.db` to `main` branch

### Manual Trigger

Run manually via GitHub Actions UI or CLI:
```bash
gh workflow run metrics.yaml
```

## License

Licensed under Apache-2.0 OR MIT.
