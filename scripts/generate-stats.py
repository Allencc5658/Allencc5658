"""Generate four sky-blue cards from public REST data with bounded retries."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import escape
from http.client import HTTPException
import json
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
import xml.etree.ElementTree as ET

USERNAME = "Allencc5658"
API = "https://api.github.com"
MAX_REPO_PAGES = 5
MAX_LANGUAGE_REPOS = 45
THEMES = {
    "light": {"bg": "#ffffff", "border": "#bae6fd", "title": "#0284c7", "body": "#334155", "muted": "#64748b", "tint": "#f0f9ff"},
    "dark": {"bg": "#0d1117", "border": "#164e63", "title": "#7dd3fc", "body": "#cbd5e1", "muted": "#94a3b8", "tint": "#082f49"},
}
COLORS = ["#0284c7", "#38bdf8", "#7dd3fc", "#0369a1", "#0ea5e9", "#bae6fd"]
ICONS = [
    '<rect x="2" y="2" width="12" height="13" rx="2"/><path d="M5 2v13M5 12h9"/>',
    '<path d="m8 1.5 2.1 4.3 4.8.7-3.5 3.4.8 4.8L8 12.4l-4.2 2.3.8-4.8L1.1 6.5l4.8-.7Z"/>',
    '<circle cx="6" cy="5" r="2.5"/><path d="M1 14v-1a5 5 0 0 1 10 0v1M11 3a2.5 2.5 0 0 1 0 5M13 10a4 4 0 0 1 2 4"/>',
]


def nonnegative_int(value, label):
    if type(value) is not int or value < 0:
        raise ValueError(f"Invalid nonnegative integer for {label}")
    return value


class GitHubRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # An authenticated request must never forward its token to another host.
        target = urlsplit(newurl)
        if target.scheme != "https" or target.netloc != "api.github.com":
            raise HTTPError(req.full_url, 403, "Blocked redirect outside GitHub API", headers, None)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class PublicAPI:
    MAX_ATTEMPTS = 4
    MAX_RETRY_WAIT = 180  # Shared across the whole statistics build, in seconds.

    def __init__(self, token=None):
        self.token = (os.environ.get("GITHUB_TOKEN", "") if token is None else token).strip()
        if os.environ.get("GITHUB_ACTIONS") == "true" and not self.token:
            raise RuntimeError("GITHUB_TOKEN is missing in Actions; keeping published images.")
        self.opener = build_opener(ProxyHandler({}), GitHubRedirectHandler())
        self.waited = 0

    def safe_message(self, value):
        text = str(value)
        if self.token:
            text = text.replace(self.token, "[REDACTED]")
        return " ".join(text.split())[:300]

    def delay(self, headers, attempt, rate_limited):
        delays = []
        retry_after = headers.get("Retry-After")
        if retry_after is not None:
            try:
                delays.append(max(0, int(retry_after)))
            except ValueError:
                try:
                    delays.append(max(0, parsedate_to_datetime(retry_after).timestamp() - time.time() + 1))
                except (TypeError, ValueError, OverflowError):
                    pass
        if headers.get("X-RateLimit-Remaining") == "0":
            try:
                delays.append(max(0, int(headers["X-RateLimit-Reset"]) - time.time() + 1))
            except (KeyError, ValueError, OverflowError):
                pass
        # A secondary limit without usable timing information requires >= 60s.
        fallback = (60 if rate_limited else 2) * 2 ** (attempt - 1)
        return max([2 ** attempt, *delays]) if delays else fallback

    def retry(self, detail, attempt, delay):
        print(f"GitHub API attempt {attempt}/{self.MAX_ATTEMPTS}: {detail}", file=sys.stderr)
        if attempt >= self.MAX_ATTEMPTS:
            raise RuntimeError(f"{detail}; retry attempts exhausted; keeping published images.") from None
        if self.waited + delay > self.MAX_RETRY_WAIT:
            raise RuntimeError(
                f"{detail}; required wait {delay:.0f}s exceeds remaining retry budget "
                f"{self.MAX_RETRY_WAIT - self.waited:.0f}s; keeping published images."
            ) from None
        print(f"Retrying after {delay:.0f}s.", file=sys.stderr)
        time.sleep(delay)
        self.waited += delay

    def get(self, path):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Allencc5658-profile-public-stats",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            request = Request(API + path, headers=headers)
            try:
                with self.opener.open(request, timeout=30) as response:
                    result = json.load(response)
                    return result, response.headers.get("Link", "")
            except HTTPError as error:
                response_headers = error.headers or {}
                try:
                    payload = json.loads(error.read(4096).decode("utf-8", errors="replace"))
                    message = payload.get("message", error.reason) if isinstance(payload, dict) else error.reason
                except (ValueError, OSError, HTTPException):
                    message = error.reason
                finally:
                    error.close()
                rate_limited = error.code == 429 or (error.code == 403 and (
                    response_headers.get("X-RateLimit-Remaining") == "0"
                    or response_headers.get("Retry-After") is not None
                    or "rate limit" in str(message).lower()
                    or "abuse detection" in str(message).lower()
                ))
                diagnostic = "; ".join(
                    f"{key}={self.safe_message(response_headers[key])}"
                    for key in ("X-RateLimit-Remaining", "X-RateLimit-Reset", "Retry-After", "X-GitHub-Request-Id")
                    if key in response_headers
                )
                detail = f"HTTP {error.code} for {path}: {self.safe_message(message)}"
                detail += f"; auth={'token' if self.token else 'anonymous'}"
                if diagnostic:
                    detail += f"; {diagnostic}"
                if not rate_limited and error.code not in (500, 502, 503, 504):
                    raise RuntimeError(f"{detail}; not retryable; keeping published images.") from None
                self.retry(detail, attempt, self.delay(response_headers, attempt, rate_limited))
            except (URLError, TimeoutError, ConnectionError, HTTPException, json.JSONDecodeError, UnicodeDecodeError) as error:
                detail = f"{type(error).__name__} for {path}: {self.safe_message(error)}"
                self.retry(detail, attempt, 2 ** attempt)


def fetch_summary(api):
    user, _ = api.get(f"/users/{USERNAME}")
    if not isinstance(user, dict) or user.get("login", "").lower() != USERNAME.lower():
        raise ValueError("Unexpected user response")
    repositories = []
    for page in range(1, MAX_REPO_PAGES + 1):
        batch, links = api.get(f"/users/{USERNAME}/repos?type=owner&sort=full_name&per_page=100&page={page}")
        if not isinstance(batch, list):
            raise ValueError("Expected a repository list")
        repositories.extend(batch)
        if 'rel="next"' not in links:
            break
    else:
        raise RuntimeError("Repository pagination exceeded 500 repositories; adjust limits before publishing incomplete data.")
    seen = set()
    owned = []
    for repo in repositories:
        if repo.get("private") is not False or repo.get("owner", {}).get("login", "").lower() != USERNAME.lower():
            continue
        identity = repo["id"]
        if identity in seen:
            raise ValueError("Duplicate repository across API pages; retry after repository changes settle")
        seen.add(identity)
        owned.append(repo)
    originals = [repo for repo in owned if repo["fork"] is False]
    if len(originals) > MAX_LANGUAGE_REPOS:
        raise RuntimeError("More than 45 public non-fork repositories; revise the API request budget before expanding scope.")
    languages = Counter()
    for repo in originals:
        data, _ = api.get(f"/repos/{USERNAME}/{quote(repo['name'], safe='')}/languages")
        if not isinstance(data, dict):
            raise ValueError("Expected language byte counts")
        for name, value in data.items():
            languages[name] += nonnegative_int(value, f"{repo['name']}/{name}")
    return {
        "public_repositories": len(owned),
        "nonfork_repositories": len(originals),
        "stars": sum(nonnegative_int(repo["stargazers_count"], "stars") for repo in owned),
        "followers": nonnegative_int(user["followers"], "followers"),
        "languages": dict(sorted(languages.items(), key=lambda pair: (-pair[1], pair[0]))),
    }


def svg(theme, title, description, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="440" height="210" viewBox="0 0 440 210" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title)}</title>
  <desc id="desc">{escape(description)}</desc>
  <rect x="0.5" y="0.5" width="439" height="209" rx="16" fill="{theme['bg']}" stroke="{theme['border']}"/>
  <g font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif">{body}</g>
</svg>\n'''


def render_cards(summary, date):
    metrics = [
        ("Public repositories", summary["public_repositories"]),
        ("Stars on public repositories", summary["stars"]),
        ("Followers", summary["followers"]),
    ]
    languages = [(name, count) for name, count in summary["languages"].items() if count > 0]
    total = sum(count for _, count in languages)
    if len(languages) > 6:
        languages = languages[:5] + [("Other", sum(count for _, count in languages[5:]))]
    cards = {}
    for variant, theme in THEMES.items():
        body = f'<text x="24" y="35" font-size="18" font-weight="600" fill="{theme["title"]}">GitHub Activity</text>'
        body += f'<rect x="348" y="19" width="67" height="23" rx="11.5" fill="{theme["tint"]}"/><text x="381.5" y="34.5" text-anchor="middle" font-size="10" font-weight="600" letter-spacing="1" fill="{theme["title"]}">PUBLIC</text>'
        for index, ((label, value), icon) in enumerate(zip(metrics, ICONS)):
            y = 77 + index * 30
            body += f'<g transform="translate(24 {y-13})" fill="none" stroke="{theme["title"]}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{icon}</g>'
            body += f'<text x="52" y="{y}" font-size="13.5" fill="{theme["body"]}">{label}</text>'
            body += f'<text x="413" y="{y}" text-anchor="end" font-size="15" font-weight="600" fill="{theme["body"]}">{value:,}</text>'
        body += f'<path d="M24 168H416" stroke="{theme["border"]}"/>'
        body += f'<text x="24" y="191" font-size="11.5" fill="{theme["muted"]}">Public API snapshot · {date}</text>'
        description = f'Public GitHub REST snapshot for {USERNAME} on {date}. ' + '; '.join(f'{label}: {value}' for label, value in metrics) + '. Commit, pull request and contribution totals are not represented.'
        cards[f"stats-{variant}.svg"] = svg(theme, "GitHub Activity", description, body)

        body = f'<text x="24" y="35" font-size="18" font-weight="600" fill="{theme["title"]}">Languages in Public Repos</text>'
        if total:
            body += '<defs><clipPath id="bar"><rect x="24" y="60" width="392" height="11" rx="5.5"/></clipPath></defs><g clip-path="url(#bar)">'
            position = 24.0
            for index, (_, count) in enumerate(languages):
                width = count / total * 392
                body += f'<rect x="{position:.4f}" y="60" width="{width:.4f}" height="11" fill="{COLORS[index]}"/>'
                position += width
            body += '</g>'
            for index, (name, count) in enumerate(languages):
                x, y = 28 + (index % 2) * 199, 99 + (index // 2) * 26
                short_name = name if len(name) <= 14 else name[:13] + "…"
                body += f'<circle cx="{x}" cy="{y-4}" r="4.3" fill="{COLORS[index]}"/>'
                body += f'<text x="{x+12}" y="{y}" font-size="12.5" fill="{theme["body"]}">{escape(short_name)}</text>'
                body += f'<text x="{x+182}" y="{y}" font-size="12.5" text-anchor="end" fill="{theme["muted"]}">{count/total*100:.1f}%</text>'
        else:
            body += f'<text x="24" y="95" font-size="14" fill="{theme["body"]}">No public language data yet</text>'
            body += f'<text x="24" y="120" font-size="12" fill="{theme["muted"]}">GitHub returned no code byte counts.</text>'
        body += f'<path d="M24 168H416" stroke="{theme["border"]}"/>'
        body += f'<text x="24" y="191" font-size="10.5" fill="{theme["muted"]}">Code bytes · public non-fork repos · {date}</text>'
        description = f'Public GitHub REST snapshot on {date}; {total} code bytes across {summary["nonfork_repositories"]} owned public non-fork repositories. ' + '; '.join(f'{name}: {count} bytes' for name, count in summary['languages'].items()) + '. This distribution is not a measure of proficiency.'
        cards[f"languages-{variant}.svg"] = svg(theme, "Languages in Public Repos", description, body)
    for name, content in cards.items():
        if ET.fromstring(content).tag != '{http://www.w3.org/2000/svg}svg':
            raise ValueError(f"Invalid SVG: {name}")
    return cards


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(".profile-build"))
    args = parser.parse_args()
    summary = fetch_summary(PublicAPI())
    date = datetime.now(timezone.utc).date().isoformat()
    cards = render_cards(summary, date)
    # Fetch and render the entire set before writing to the staging directory.
    # The workflow publishes only after the snake and six-file validation pass.
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in cards.items():
        (args.output_dir / name).write_text(content, encoding="utf-8")
    print(json.dumps({"date_utc": date, **summary}, ensure_ascii=False))
    print(f"Generated {len(cards)} public statistics cards in {args.output_dir}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Profile statistics failed: {error}", file=sys.stderr)
        sys.exit(1)
