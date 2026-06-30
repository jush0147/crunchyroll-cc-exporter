# Crunchyroll CC Exporter

Export **closed captions** that are already available to your Crunchyroll account, especially English dub captions exposed as `captions.en-US` in the playback response.

This project exists because many older subtitle downloaders only read Crunchyroll's `subtitles` field. For English dubs, the word-for-word accessibility captions are often in `captions`, not `subtitles`.

## What it does

- Logs in with your own Crunchyroll account **or** uses your own `etp_rt` cookie.
- Lists seasons/episodes for a series.
- Resolves the requested audio version, e.g. `en-US` dub.
- Reads the modern play response from Crunchyroll's play service.
- Downloads the selected caption track, e.g. `captions.en-US`, as VTT.
- Optionally converts VTT to SRT.
- Writes a `summary.json` report.

## What it does **not** do

- It does **not** download video.
- It does **not** decrypt or bypass DRM.
- It does **not** provide any copyrighted captions.
- It does **not** include accounts, cookies, tokens, or sample episode subtitle files.
- It does **not** make premium content available without a valid subscription.

Use this only for personal accessibility, backup, and language-learning workflows for content you are authorized to access. Do not redistribute downloaded captions.

## Install

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows Git Bash
python -m pip install -e .
```

Or install dependencies directly:

```bash
python -m pip install -r requirements.txt
```

## Quick start

### Recommended: use environment variables

```bash
export CRUNCHYROLL_EMAIL='you@example.com'
export CRUNCHYROLL_PASSWORD='your-password'

cr-cc-export \
  'https://www.crunchyroll.com/series/G4PH0WXVJ/spy-x-family' \
  --audio-lang en-US \
  --caption-lang en-US \
  --season 1-3 \
  --format both \
  --output ./outputs/spyxfamily-cc
```

### Use an `etp_rt` cookie instead of password

```bash
export CRUNCHYROLL_ETP_RT='your-etp-rt-cookie-value'

cr-cc-export SERIES_URL_OR_ID --audio-lang en-US --caption-lang en-US --format srt
```

### Dry-run/list only

```bash
cr-cc-export SERIES_URL_OR_ID --audio-lang en-US --caption-lang en-US --season 1 --dry-run
```

## CLI options

```text
usage: cr-cc-export SERIES_URL_OR_ID [options]

Authentication:
  --email EMAIL              Crunchyroll email. Can also use CRUNCHYROLL_EMAIL.
  --password PASSWORD        Crunchyroll password. Can also use CRUNCHYROLL_PASSWORD.
  --etp-rt COOKIE            Existing etp_rt cookie. Can also use CRUNCHYROLL_ETP_RT.

Selection:
  --audio-lang en-US         Audio version to inspect for captions. Default: en-US.
  --caption-lang en-US       Caption language to export. Default: en-US.
  --season 1,2,3 or 1-3      Season numbers to include. Omit for all seasons.
  --episode 1,3-5            Episode numbers to include within selected seasons.

Output:
  --format vtt|srt|both      Default: vtt.
  --output DIR               Output directory. Default: ./outputs/<series-id>.
  --dry-run                  List availability; do not download.
```

## Why captions, not subtitles?

Crunchyroll play responses may contain both:

```json
{
  "subtitles": {
    "en-US": { "url": "..." }
  },
  "captions": {
    "en-US": { "url": "..." }
  }
}
```

For English dubs, `subtitles.en-US` can be a translation subtitle that does not match the dub script. `captions.en-US` is the closed-caption track intended to match the English dub.

## Output

The tool writes files like:

```text
S01E01 - Episode Title - English CC.vtt
S01E01 - Episode Title - English CC.srt
summary.json
```

`summary.json` records episode IDs, selected dub GUIDs, available caption languages, and download status. It does not include access tokens or cookies.

## Security notes

- Prefer environment variables over command-line password arguments to avoid shell history leaks.
- Never commit `.env`, cookies, tokens, `outputs/`, `.vtt`, `.srt`, or `.zip` files.
- Change passwords that were pasted into chats or logs.

## License

MIT
