#!/usr/bin/env python3
"""
Sync Georgia Southern Folio (D2L Brightspace) calendar feed -> Notion database.

Reads three environment variables:
  ICS_URL            - your personal D2L calendar feed URL (the one ending in feed.ics?token=...)
  NOTION_API_KEY      - a Notion internal integration secret
  NOTION_DATABASE_ID  - the ID of the target Notion database

For every event in the feed it either creates a new Notion page or updates
an existing one (matched by the D2L event UID stored in the "D2L UID"
property). It never touches the "Done" or "Priority" properties on an
update, so your own checkmarks and priorities are never overwritten.

Recurring class meetings (lectures/office hours) and "- Available" openings
are skipped since they aren't deadlines.
"""

import os
import re
import sys
from datetime import datetime, date

import requests
from icalendar import Calendar

ICS_URL = os.environ["ICS_URL"]
NOTION_API_KEY = os.environ["NOTION_API_KEY"]
NOTION_DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

NOTION_VERSION = "2022-06-28"
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

COURSE_RE = re.compile(r"\(([A-Z]{2,5})-(\d{3,4})[A-Za-z0-9-]*\)\s*$")


def fetch_calendar():
    resp = requests.get(ICS_URL, timeout=30)
    resp.raise_for_status()
    return Calendar.from_ical(resp.text)


def classify_type(summary: str, description: str) -> str:
    desc = description or ""
    if "attendance verification" in summary.lower():
        return "Attendance"
    if "Quizzes:" in desc:
        return "Quiz"
    if "Discussions:" in desc:
        return "Discussion"
    if "Assignments:" in desc:
        return "Activity" if "activity" in summary.lower() else "Assignment"
    if "Materials:" in desc:
        return "Assignment"
    return "Other"


def extract_course(location: str) -> str:
    if not location:
        return ""
    match = COURSE_RE.search(location)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return location


def extract_link(description: str) -> str:
    if not description:
        return ""
    match = re.search(r"View event - (https://\S+)", description)
    if match:
        return match.group(1).rstrip("\\")
    return ""


def clean_title(summary: str) -> str:
    if summary.endswith(" - Due"):
        return summary[: -len(" - Due")]
    return summary


def should_skip(component) -> bool:
    summary = str(component.get("summary", ""))
    if component.get("rrule") is not None:
        return True  # recurring class meeting
    if summary.lower().startswith("lecture"):
        return True
    if "office hours" in summary.lower():
        return True
    if "- available" in summary.lower():
        return True
    return False


def notion_find_page(uid: str):
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    body = {"filter": {"property": "D2L UID", "rich_text": {"equals": uid}}}
    resp = requests.post(url, headers=NOTION_HEADERS, json=body, timeout=30)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return results[0]["id"] if results else None


def build_properties(title, course, type_, due_iso, is_datetime, link, uid):
    props = {
        "Assignment": {"title": [{"text": {"content": title[:2000]}}]},
        "Course": {"rich_text": [{"text": {"content": course[:2000]}}]},
        "Type": {"select": {"name": type_}},
        "Due Date": {"date": {"start": due_iso}},
        "D2L UID": {"rich_text": [{"text": {"content": uid}}]},
    }
    if link:
        props["Link"] = {"url": link}
    return props


def notion_create_page(properties):
    url = "https://api.notion.com/v1/pages"
    body = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {**properties, "Done": {"checkbox": False}},
    }
    resp = requests.post(url, headers=NOTION_HEADERS, json=body, timeout=30)
    resp.raise_for_status()


def notion_update_page(page_id, properties):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    resp = requests.patch(url, headers=NOTION_HEADERS, json={"properties": properties}, timeout=30)
    resp.raise_for_status()


def main():
    cal = fetch_calendar()
    created, updated, skipped = 0, 0, 0

    for component in cal.walk("VEVENT"):
        if should_skip(component):
            skipped += 1
            continue

        uid = str(component.get("uid"))
        summary = str(component.get("summary", "")).strip()
        description = str(component.get("description", "") or "")
        location = str(component.get("location", "") or "")
        dtstart = component.get("dtstart").dt

        if isinstance(dtstart, datetime):
            due_iso = dtstart.isoformat()
            is_dt = True
        elif isinstance(dtstart, date):
            due_iso = dtstart.isoformat()
            is_dt = False
        else:
            continue

        title = clean_title(summary)
        course = extract_course(location)
        type_ = classify_type(summary, description)
        link = extract_link(description)

        properties = build_properties(title, course, type_, due_iso, is_dt, link, uid)

        existing_page_id = notion_find_page(uid)
        if existing_page_id:
            notion_update_page(existing_page_id, properties)
            updated += 1
        else:
            notion_create_page(properties)
            created += 1

    print(f"Done. Created {created}, updated {updated}, skipped {skipped} (class meetings / openings).")


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print(f"Notion/D2L API error: {e.response.status_code} {e.response.text}", file=sys.stderr)
        sys.exit(1)
