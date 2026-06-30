from __future__ import annotations

import base64
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Iterable

import cloudscraper

from .convert import vtt_to_srt
from .models import CaptionResult

BASE_API = "https://beta-api.crunchyroll.com"
BASE_WEB = "https://www.crunchyroll.com"
SSO_LOGIN = "https://sso.crunchyroll.com/login"
SSO_LOGIN_API = "https://sso.crunchyroll.com/api/login"
PLAY_URL = "https://cr-play-service.prd.crunchyrollsvc.com/v1/{guid}/web/firefox/play"
TOKEN_URL = f"{BASE_API}/auth/v1/token"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/126 Safari/537.36"
)


class CrunchyrollError(RuntimeError):
    pass


def extract_series_id(value: str) -> str:
    match = re.search(r"/series/([A-Z0-9]+)", value)
    if match:
        return match.group(1)
    if re.fullmatch(r"[A-Z0-9]{8,}", value):
        return value
    raise CrunchyrollError(f"Could not extract series id from: {value}")


def parse_number_filter(spec: str | None) -> set[int] | None:
    if not spec:
        return None
    selected: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            selected.update(range(int(start), int(end) + 1))
        else:
            selected.add(int(part))
    return selected


def safe_filename(value: Any) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]+", "_", str(value)).strip(" .")
    return cleaned[:120] or "untitled"


class CrunchyrollClient:
    def __init__(self, user_agent: str = USER_AGENT) -> None:
        self.user_agent = user_agent
        self.session = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "desktop": True}
        )
        self.session.headers.update({"User-Agent": self.user_agent})
        self.access_token: str | None = None
        self.account_id: str | None = None
        self.country: str | None = None

    @property
    def auth_headers(self) -> dict[str, str]:
        if not self.access_token:
            raise CrunchyrollError("Not authenticated")
        return {"Authorization": f"Bearer {self.access_token}", "User-Agent": self.user_agent}

    def login(self, *, email: str | None = None, password: str | None = None, etp_rt: str | None = None) -> None:
        if etp_rt:
            self.session.cookies.set("etp_rt", etp_rt, domain=".crunchyroll.com")
        elif email and password:
            self._login_sso(email, password)
        else:
            raise CrunchyrollError("Provide email/password or etp_rt")
        self._exchange_etp_rt()

    def _login_sso(self, email: str, password: str) -> None:
        self.session.get(SSO_LOGIN, timeout=30)
        response = self.session.post(
            SSO_LOGIN_API,
            headers={
                "Content-Type": "application/json",
                "Origin": "https://sso.crunchyroll.com",
                "Referer": SSO_LOGIN,
                "User-Agent": self.user_agent,
            },
            json={
                "email": email,
                "password": password,
                "recaptchaToken": "",
                "eventSettings": {},
            },
            timeout=30,
        )
        if response.status_code != 200:
            raise CrunchyrollError(f"SSO login failed: HTTP {response.status_code} {response.text[:200]}")
        payload = response.json()
        if payload.get("status") != "ok":
            raise CrunchyrollError(f"SSO login failed: {payload}")
        if not self.session.cookies.get("etp_rt"):
            raise CrunchyrollError("SSO login succeeded but did not return etp_rt cookie")

    def _exchange_etp_rt(self) -> None:
        homepage = self.session.get(BASE_WEB + "/", timeout=30).text
        match = re.search(r'"accountAuthClientId":"([_a-z0-9]+)"', homepage)
        if not match:
            raise CrunchyrollError("Could not find accountAuthClientId on Crunchyroll homepage")
        basic = "Basic " + base64.b64encode(f"{match.group(1)}:".encode()).decode()
        response = self.session.post(
            TOKEN_URL,
            headers={
                "Authorization": basic,
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": self.user_agent,
            },
            data={
                "device_id": str(uuid.uuid4()),
                "device_type": "Firefox on Windows",
                "grant_type": "etp_rt_cookie",
            },
            timeout=30,
        )
        if response.status_code != 200:
            raise CrunchyrollError(f"Token exchange failed: HTTP {response.status_code} {response.text[:200]}")
        payload = response.json()
        self.access_token = payload["access_token"]
        self.account_id = payload.get("account_id")
        self.country = payload.get("country")

    def get_json(self, url: str, **params: Any) -> dict[str, Any]:
        response = self.session.get(url, headers=self.auth_headers, params=params, timeout=30)
        if response.status_code != 200:
            raise CrunchyrollError(f"GET {url} failed: HTTP {response.status_code} {response.text[:200]}")
        return response.json()

    def iter_episodes(
        self,
        series_id: str,
        *,
        audio_lang: str,
        seasons: set[int] | None,
        episodes: set[int] | None,
    ) -> Iterable[dict[str, Any]]:
        season_data = self.get_json(
            f"{BASE_API}/content/v2/cms/series/{series_id}/seasons",
            force_locale="",
            preferred_audio_language=audio_lang,
            locale="en-US",
        )["data"]
        for season in season_data:
            season_number = season.get("season_number") or season.get("season_sequence_number")
            if seasons and int(season_number) not in seasons:
                continue
            episode_data = self.get_json(
                f"{BASE_API}/content/v2/cms/seasons/{season['id']}/episodes",
                preferred_audio_language=audio_lang,
                locale="en-US",
            )["data"]
            for episode in episode_data:
                ep_number = episode.get("episode_number") or episode.get("sequence_number") or episode.get("episode")
                try:
                    ep_int = int(float(ep_number))
                except (TypeError, ValueError):
                    ep_int = None
                if episodes and ep_int not in episodes:
                    continue
                yield {"season_number": int(season_number), "episode": episode}

    def fetch_play_response(self, guid: str) -> tuple[int, dict[str, Any] | None, str | None]:
        response = self.session.get(PLAY_URL.format(guid=guid), headers=self.auth_headers, timeout=30)
        if response.status_code != 200:
            return response.status_code, None, response.text[:200]
        return response.status_code, response.json(), None

    def release_stream(self, guid: str, token: str | None) -> None:
        if not token:
            return
        for url in (
            f"{BASE_API}/playback/v1/token/{guid}/{token}",
            f"{BASE_WEB}/playback/v1/token/{guid}/{token}",
        ):
            try:
                self.session.delete(url, headers=self.auth_headers, timeout=10)
            except Exception:
                pass


def export_captions(
    client: CrunchyrollClient,
    series: str,
    *,
    output: Path,
    audio_lang: str = "en-US",
    caption_lang: str = "en-US",
    season_spec: str | None = None,
    episode_spec: str | None = None,
    output_format: str = "vtt",
    dry_run: bool = False,
    delay: float = 0.15,
) -> dict[str, Any]:
    series_id = extract_series_id(series)
    output.mkdir(parents=True, exist_ok=True)
    seasons = parse_number_filter(season_spec)
    episodes = parse_number_filter(episode_spec)
    results: list[CaptionResult] = []

    for item in client.iter_episodes(series_id, audio_lang=audio_lang, seasons=seasons, episodes=episodes):
        season_number = item["season_number"]
        episode = item["episode"]
        versions = {
            version.get("audio_locale"): version.get("guid")
            for version in episode.get("versions", [])
            if version.get("audio_locale") and version.get("guid")
        }
        if episode.get("audio_locale"):
            versions[episode.get("audio_locale")] = episode["id"]
        selected_guid = versions.get(audio_lang) or episode["id"]
        ep_number = episode.get("episode_number") or episode.get("sequence_number") or episode.get("episode")
        files: list[str] = []
        status, play_response, error = client.fetch_play_response(selected_guid)
        captions = play_response.get("captions", {}) if play_response else {}
        subtitles = play_response.get("subtitles", {}) if play_response else {}
        downloaded = False
        try:
            caption = captions.get(caption_lang) or next(
                (value for key, value in captions.items() if str(key).lower().startswith(caption_lang.split("-")[0].lower())),
                None,
            )
            if caption and caption.get("url") and not dry_run:
                response = client.session.get(caption["url"], timeout=30)
                if response.status_code != 200 or not response.text.strip():
                    error = f"caption download HTTP {response.status_code}, empty={not bool(response.text.strip())}"
                else:
                    stem = f"S{season_number:02d}E{int(float(ep_number)):02d} - {safe_filename(episode.get('title'))} - English CC"
                    if output_format in {"vtt", "both"}:
                        vtt_path = output / f"{stem}.vtt"
                        vtt_path.write_text(response.text, encoding="utf-8")
                        files.append(str(vtt_path))
                    if output_format in {"srt", "both"}:
                        srt_path = output / f"{stem}.srt"
                        srt_path.write_text(vtt_to_srt(response.text), encoding="utf-8")
                        files.append(str(srt_path))
                    downloaded = True
            elif not caption:
                error = error or f"caption language {caption_lang} not available"
        finally:
            if play_response:
                client.release_stream(selected_guid, play_response.get("token"))
        results.append(
            CaptionResult(
                season=season_number,
                episode=ep_number,
                title=episode.get("title", ""),
                base_id=episode["id"],
                selected_guid=selected_guid,
                play_status=status,
                caption_languages=list(captions.keys()),
                subtitle_languages=list(subtitles.keys()),
                downloaded=downloaded,
                files=files,
                error=error,
            )
        )
        if delay:
            time.sleep(delay)

    summary = {
        "series_id": series_id,
        "country": client.country,
        "account_id_present": bool(client.account_id),
        "output": str(output),
        "total": len(results),
        "downloaded": sum(result.downloaded for result in results),
        "with_requested_caption": sum(caption_lang in result.caption_languages for result in results),
        "results": [result.__dict__ for result in results],
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
