"""
fetch_war_news.py
-----------------
Fetches war/conflict-related articles from the New York Times RSS feed.
Filters by war-related keywords and saves to /home/mimou/airflow/mid-semester/data/war_news.csv
"""

import os
import re
import feedparser
import pandas as pd
from datetime import datetime, date
from email.utils import parsedate_to_datetime

DATA_DIR = os.environ.get("AIRFLOW_DATA_DIR", "/home/mimou/airflow/mid-semester/data")
OUTPUT_FILE = os.path.join(DATA_DIR, "war_news.csv")

# NYT RSS feeds most likely to contain war/conflict content
NYT_RSS_FEEDS = [
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/MiddleEast.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Europe.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/US.xml",
]

# Keywords that indicate war / conflict content
WAR_KEYWORDS = [
    "war", "conflict", "military", "attack", "strike", "bomb", "missile",
    "troops", "soldier", "combat", "invasion", "battle", "offensive",
    "ceasefire", "airstrike", "explosion", "terror", "terrorist",
    "genocide", "sanction", "nato", "army", "navy", "drone", "artillery",
    "insurgent", "rebel", "hostage", "refugee", "ukraine", "russia",
    "israel", "gaza", "hamas", "hezbollah", "iran", "syria", "iraq",
    "afghanistan", "coup", "massacre", "civilian", "casualties",
]

START_DATE = date(2024, 1, 1)

#What It Does
#Checks if a piece of text contains ANY war-related word. 
#Returns True or False.
def _is_war_related(text: str) -> bool:
    """Return True if the text contains any war-related keyword."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in WAR_KEYWORDS)

#What It Does
#Extracts the publication date from an RSS article entry. 
#Returns a date object or None if it fails.
def _parse_pub_date(entry) -> date | None:
    """Extract publication date from an RSS entry."""
    try:
        if hasattr(entry, "published"):
            #Converts the RSS date string into a Python datetime object:
            dt = parsedate_to_datetime(entry.published)
            return dt.date()
        if hasattr(entry, "updated"):
            dt = parsedate_to_datetime(entry.updated)
            return dt.date()
    except Exception:
        pass
    return None


def fetch_and_save_war_news(
    feeds: list[str] = NYT_RSS_FEEDS,
    output_path: str = OUTPUT_FILE,
    start_date: date = START_DATE,
) -> str:
    """
    Fetches and filters war-related news from NYT RSS feeds.

    Parameters
    ----------
    feeds      : List of NYT RSS feed URLs to parse
    output_path: Where to save the resulting CSV
    start_date : Ignore articles published before this date

    Returns
    -------
    str: Path to the saved CSV file
    """
    #Creates the `data/` folder if it does not exist yet:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)


    #records — empty list that will collect all war articles
    records = []
    #seen_links — empty set to track URLs we already processed (prevents duplicates)
    seen_links = set()
    
    #feeds: list[str] = NYT_RSS_FEEDS,
    for feed_url in feeds:
        print(f"Parsing feed: {feed_url}")
        try:
            #THE API CALL. Makes HTTP GET request to NYT URL,
            #downloads XML, parses all articles and returns them as
            #Python objects with .title, .summary, .link
            feed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"  WARNING: Could not parse {feed_url}: {e}")
            continue

        for entry in feed.entries:
            title = getattr(entry, "title", "") or ""
            summary = getattr(entry, "summary", "") or ""
            link = getattr(entry, "link", "") or ""
            combined_text = f"{title} {summary}"

            # Deduplicate
            if link in seen_links:
                continue
            seen_links.add(link)

            # Filter by war keywords(The Function "_is_war_related")
            if not _is_war_related(combined_text):
                continue

            # Filter by date(The function "_parse_pub_date")
            pub_date = _parse_pub_date(entry)
            if pub_date and pub_date < start_date:
                continue

            records.append({
                "date": pub_date,
                "title": title.strip(),
                "summary": re.sub(r"<[^>]+>", "", summary).strip(),  # strip HTML tags
                "link": link,
            })

    if not records:
        print("WARNING: No war-related articles found. Creating empty CSV with headers.")
        df = pd.DataFrame(columns=["date", "title", "summary", "link"])
    else:
        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"])
        df = df.dropna(subset=["date"])
        df = df.sort_values("date").reset_index(drop=True)

    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} war-related articles → {output_path}")
    return output_path


# ── standalone execution ───────────────────────────────────────────────
if __name__ == "__main__":
    path = fetch_and_save_war_news()
    df = pd.read_csv(path)
    print(df[["date", "title"]].tail(10))
