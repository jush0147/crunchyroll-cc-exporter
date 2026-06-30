from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EpisodeSelection:
    season: int
    episode: str | int | float | None
    title: str
    base_id: str
    selected_guid: str


@dataclass(frozen=True)
class CaptionResult:
    season: int
    episode: str | int | float | None
    title: str
    base_id: str
    selected_guid: str
    play_status: int | None
    caption_languages: list[str]
    subtitle_languages: list[str]
    downloaded: bool
    files: list[str]
    error: str | None = None
