from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path

from . import __version__
from .crunchyroll import CrunchyrollClient, CrunchyrollError, export_captions, extract_series_id


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cr-cc-export",
        description="Export Crunchyroll closed-caption tracks available to your account as VTT/SRT.",
    )
    parser.add_argument("series", help="Crunchyroll series URL or series id, e.g. G4PH0WXVJ")
    parser.add_argument("--email", default=os.getenv("CRUNCHYROLL_EMAIL"), help="Crunchyroll email. Can also use CRUNCHYROLL_EMAIL.")
    parser.add_argument("--password", default=os.getenv("CRUNCHYROLL_PASSWORD"), help="Crunchyroll password. Prefer CRUNCHYROLL_PASSWORD to avoid shell history.")
    parser.add_argument("--etp-rt", default=os.getenv("CRUNCHYROLL_ETP_RT"), help="Existing etp_rt cookie. Can also use CRUNCHYROLL_ETP_RT.")
    parser.add_argument("--audio-lang", default="en-US", help="Audio version to inspect. Default: en-US.")
    parser.add_argument("--caption-lang", default="en-US", help="Caption language to export. Default: en-US.")
    parser.add_argument("--season", dest="season_spec", help="Season numbers, e.g. 1,2,3 or 1-3. Omit for all.")
    parser.add_argument("--episode", dest="episode_spec", help="Episode numbers within selected seasons, e.g. 1,3-5.")
    parser.add_argument("--format", choices=["vtt", "srt", "both"], default="vtt", help="Output format. Default: vtt.")
    parser.add_argument("--output", type=Path, help="Output directory. Default: ./outputs/<series-id>.")
    parser.add_argument("--dry-run", action="store_true", help="List availability; do not download caption files.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    output = args.output or Path("outputs") / extract_series_id(args.series)

    password = args.password
    if args.email and not password and not args.etp_rt:
        password = getpass.getpass("Crunchyroll password: ")

    try:
        client = CrunchyrollClient()
        client.login(email=args.email, password=password, etp_rt=args.etp_rt)
        summary = export_captions(
            client,
            args.series,
            output=output,
            audio_lang=args.audio_lang,
            caption_lang=args.caption_lang,
            season_spec=args.season_spec,
            episode_spec=args.episode_spec,
            output_format=args.format,
            dry_run=args.dry_run,
        )
    except CrunchyrollError as exc:
        parser.exit(2, f"error: {exc}\n")

    print(json.dumps({key: summary[key] for key in ["series_id", "country", "output", "total", "downloaded", "with_requested_caption"]}, ensure_ascii=False, indent=2))
    print(f"summary: {output / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
