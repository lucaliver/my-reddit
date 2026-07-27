# my-reddit

A serverless, automated Reddit digest built with Python and Vanilla JS. It fetches posts from configured subreddits via RSS, filters/groups them and generates a static JSON payload consumed by a responsive front-end. Designed to bypass Reddit's strict JSON API Cloudflare blocks by securely parsing RSS content payloads.

## Features

- **Automated Pipeline:** GitHub Actions runs a Python script weekly (or on demand) to fetch, filter and compile posts.
- **Resilient Fetching:** Uses Reddit's `.rss` feeds instead of `.json` endpoints to prevent `HTTP 403 Forbidden` errors triggered by Cloudflare. Text excerpts and thumbnails are extracted directly from the RSS HTML content.
- **Smart Filtering & Grouping:**
  - Filters by age (`MIN_AGE_HOURS`, `MAX_AGE_HOURS`) and blocked keywords.
  - Groups subreddits into custom categories.
  - Caps posts per group (`MAX_POSTS_PER_GROUP`) and limits posts per individual subreddit (`MAX_POSTS_PER_SUBREDDIT`) for a balanced digest.
- **Dual View UI:**
  - **Grouped View:** Classic clustered view with a smart expand/collapse toggle.
  - **Feed View:** A flat, chronological scrolling feed (Reddit style) featuring a horizontal group filter carousel.
- **Local State Tracking:** Uses `localStorage` to track read posts and update unread counts seamlessly across views.

## Live Demo

👉 **[lucaliver.github.io/my-reddit](https://lucaliver.github.io/my-reddit)**

## Architecture

```text
my-reddit/
├── main.py                  # Pipeline orchestrator
├── config.py                # Environment-driven configuration
├── requirements.txt         # Dependencies (requests, python-dotenv)
├── src/
│   ├── reddit_client.py     # RSS fetching & HTML extraction (thumbnails/excerpts)
│   ├── filter.py            # Age & keyword filtering
│   ├── grouper.py           # Grouping logic & distribution caps
│   └── site_generator.py    # Serializes output to digest.json
├── site/
│   ├── index.html           # Landing page shell
│   ├── style.css            # Dark-mode design system & View toggle styling
│   └── app.js               # Client-side renderer (Views, Filters, State)
└── .github/workflows/
    └── weekly_digest.yml    # CI/CD automation
```

## Configuration

Control the pipeline behavior using environment variables (or `.env` locally).

| Variable                  | Default       | Description                                                         |
| ------------------------- | ------------- | ------------------------------------------------------------------- |
| `SUBREDDITS`              | `[]`          | JSON array of individual subreddits.                                |
| `SUBREDDIT_GROUPS`        | _(config.py)_ | JSON mapping of group names to subreddit lists.                     |
| `FEED_SORT`               | `top`         | RSS sorting (`hot`, `new`, `top`). Reddit handles sorting natively. |
| `FETCH_LIMIT`             | `100`         | Max posts per RSS request batch.                                    |
| `MIN_AGE_HOURS`           | `12`          | Discard posts younger than this threshold.                          |
| `MAX_AGE_HOURS`           | `168`         | Discard posts older than this threshold (168h = 7 days).            |
| `MAX_POSTS_PER_GROUP`     | `10`          | Total posts capped per category group.                              |
| `MAX_POSTS_PER_SUBREDDIT` | `3`           | Prevents a single subreddit from dominating a group.                |
| `BLOCKED_KEYWORDS`        | `["trump"]`   | JSON array of keywords to ban from post titles.                     |
| `OUTPUT_DIR`              | `site`        | Destination directory for the generated `digest.json`.              |

## Local Development

```bash
# 1. Clone the repository
git clone https://github.com/lucaliver/my-reddit.git
cd my-reddit

# 2. Setup Virtual Environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. (Optional) Override defaults from config.py via a .env file

# 4. Execute the pipeline
python3 main.py

# 5. Serve the static frontend locally
python3 -m http.server 8000 --directory site --bind 0.0.0.0
```

## Deployment (GitHub Pages)

1. Navigate to **Settings → Pages** and set the Source to **GitHub Actions**.
2. Configure repository variables under **Settings → Secrets and variables → Actions** to override defaults (`SUBREDDITS`, `SUBREDDIT_GROUPS`, etc).
3. The workflow runs every Sunday at 18:00 CEST or can be triggered manually from the **Actions** tab.

## License

Personal project — feel free to fork, customize and deploy.
