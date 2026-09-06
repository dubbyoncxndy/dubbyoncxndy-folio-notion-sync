# Folio → Notion Assignment Sync

Keeps your Notion database in sync with your Georgia Southern Folio (D2L)
calendar feed automatically, for free, using GitHub Actions.

Your Notion database is already created: **School Assignments (Folio Sync)**.
It already has your first ~2.5 months of assignments loaded. This automation
keeps it updated going forward without you touching anything.

## One-time setup (about 10 minutes)

### 1. Create a private GitHub repo
- Go to github.com → New repository → make it **Private**.
- Upload these three files to the root of the repo:
  - `sync_folio_to_notion.py`
  - `requirements.txt`
  - `sync-assignments.yml` → put this one inside a folder named
    `.github/workflows/` (GitHub only runs workflow files from that exact path).

### 2. Create a Notion integration (so the script can write to your database)
- Go to https://www.notion.so/my-integrations
- Click **New integration**, give it any name (e.g. "Folio Sync"), submit.
- Copy the **Internal Integration Secret** — this is your `NOTION_API_KEY`.

### 3. Share your database with the integration
- Open the "School Assignments (Folio Sync)" database in Notion.
- Click the **•••** menu (top right) → **Connections** → add the integration
  you just created.
- Without this step, the script gets a "not found" error when it tries to
  write to the database.

### 4. Get your database ID
- The database ID is: `52d47e670840421db97d9d3480693b46`
- (This is already the one I created for you — no need to look it up.)

### 5. Add secrets to your GitHub repo
In your repo: **Settings → Secrets and variables → Actions → New repository secret**.
Add three secrets:

| Secret name | Value |
|---|---|
| `ICS_URL` | Your D2L calendar feed URL (the one ending in `feed.ics?token=...`) |
| `NOTION_API_KEY` | The integration secret from step 2 |
| `NOTION_DATABASE_ID` | `52d47e670840421db97d9d3480693b46` |

### 6. Turn it on
- Go to the **Actions** tab in your repo. GitHub sometimes asks you to
  confirm you want to enable workflows — click enable.
- Click into "Sync Folio assignments to Notion" → **Run workflow** to test it
  manually the first time.
- After that, it runs automatically every 3 hours, all year, for free.

## What it does each run

- Downloads your Folio calendar feed.
- Skips recurring lecture/office-hour meetings and "materials available"
  notices (not real deadlines).
- For everything else, creates a new row in Notion if it hasn't seen that
  assignment before, or updates the due date/title/link if Folio changed it.
- Never touches your **Done** checkbox or **Priority** field once you've set
  them — those stay yours to manage.

## Adjusting the schedule

Edit the `cron` line in `sync-assignments.yml`. Some examples:
- `"0 * * * *"` — every hour
- `"0 6,18 * * *"` — twice a day (6am and 6pm UTC)

## If something breaks

Check the **Actions** tab → click the failed run → expand "Run sync" to see
the error. Most common issues:
- Forgot to share the database with the integration (step 3)
- A secret name doesn't match exactly (case-sensitive)
