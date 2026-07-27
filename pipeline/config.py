"""Repo-wide paths and the feed registry (data/feeds.yml) loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
BUILD_DIR = DATA_DIR / "build"
FEEDS_FILE = DATA_DIR / "feeds.yml"


@dataclass(frozen=True)
class CensusConfig:
    state_fips: str
    county_fips: str


@dataclass(frozen=True)
class FeedConfig:
    id: str
    name: str
    region: str
    agency_timezone: str
    source_url: str
    license: str
    raw_path: Path
    census: CensusConfig | None

    @property
    def build_dir(self) -> Path:
        return BUILD_DIR / self.id


def load_feeds(feeds_file: Path = FEEDS_FILE) -> list[FeedConfig]:
    raw = yaml.safe_load(feeds_file.read_text(encoding="utf-8"))
    feeds = []
    for entry in raw["feeds"]:
        census = entry.get("census")
        feeds.append(
            FeedConfig(
                id=entry["id"],
                name=entry["name"],
                region=entry["region"],
                agency_timezone=entry["agency_timezone"],
                source_url=entry["source_url"],
                license=entry["license"],
                raw_path=REPO_ROOT / entry["raw_path"],
                census=CensusConfig(**census) if census else None,
            )
        )
    return feeds


def get_feed(feed_id: str, feeds_file: Path = FEEDS_FILE) -> FeedConfig:
    for feed in load_feeds(feeds_file):
        if feed.id == feed_id:
            return feed
    raise KeyError(f"Unknown feed id '{feed_id}'. Check data/feeds.yml.")
