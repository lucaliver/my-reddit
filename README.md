# 📰 my-reddit

A personalised **weekly Reddit digest** — auto-generated via GitHub Actions and served as a beautiful static landing page on **GitHub Pages**.

## How it works

```
⏰ GitHub Action (every Sunday 18:00 CEST)
   → 🐍 Python fetches posts via Reddit RSS
   → 🔍 Filters by age (last 7 days) & blocked keywords
   → 📂 Groups by category
   → 📄 Generates digest.json
   → 🚀 Deploys to GitHub Pages
```

The landing page (`site/`) loads `digest.json` client-side and renders the grouped posts with a premium dark-mode UI.

## Live Site

👉 **[lucaliver.github.io/my-reddit](https://lucaliver.github.io/my-reddit)**

## Project Structure

```
my-reddit/
├── main.py                  # Entry point — orchestrates the pipeline
├── config.py                # All configuration (env-driven)
├── requirements.txt         # Python dependencies
├── src/
│   ├── reddit_client.py     # Fetches posts via Reddit RSS feeds
│   ├── filter.py            # Age & keyword filtering
│   ├── grouper.py           # Groups posts by category
│   └── site_generator.py    # Generates digest.json for the site
├── site/
│   ├── index.html           # Landing page shell
│   ├── style.css            # Dark-mode design system
│   └── app.js               # Client-side renderer
└── .github/workflows/
    └── weekly_digest.yml     # GitHub Actions workflow
```

## Configuration

All settings are configurable via environment variables (or a `.env` file for local runs):

| Variable | Default | Description |
|---|---|---|
| `SUBREDDITS` | `[]` | JSON array of subreddit names |
| `SUBREDDIT_GROUPS` | *(see config.py)* | JSON object mapping group names → subreddit lists |
| `FEED_SORT` | `top` | RSS sort: `hot`, `new`, `top`, `rising` |
| `FETCH_LIMIT` | `100` | Max posts per RSS request |
| `MIN_AGE_HOURS` | `0` | Discard posts younger than this |
| `MAX_AGE_HOURS` | `168` | Discard posts older than this (168h = 7 days) |
| `MAX_POSTS_PER_GROUP` | `10` | Max posts shown per group |
| `BLOCKED_KEYWORDS` | `["trump"]` | JSON array of title keywords to filter out |
| `OUTPUT_DIR` | `site` | Directory for generated digest.json |

## Local Development

```bash
# 1. Clone and enter the project
git clone https://github.com/lucaliver/my-reddit.git
cd my-reddit

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and configure environment
cp .env.example .env
# Edit .env with your preferences

# 5. Run the pipeline
python main.py

# 6. Preview the site (serves site/ on localhost:8000)
python -m http.server 8000 --directory site
```

## GitHub Setup

1. **Enable GitHub Pages**: Go to repo Settings → Pages → Source: **GitHub Actions**
2. **Set repository variables** (optional): Settings → Secrets and variables → Actions → Variables tab
   - `SUBREDDITS` — override default subreddit list
   - `SUBREDDIT_GROUPS` — override default groups
3. **Trigger manually**: Actions tab → "Weekly Reddit Digest" → Run workflow

The workflow runs automatically every Sunday at 18:00 CEST.

## License

Personal project — feel free to fork and adapt.
