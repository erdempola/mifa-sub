#!/usr/bin/env python3
import re
import sys
import base64
import urllib.request

CHANNEL = "mifa_world"
LINK_PATTERN = re.compile(r"https?://mifa\.world/[a-zA-Z0-9/_-]+")
SOURCES = [
    f"https://t.me/s/{CHANNEL}",
    f"https://telegram.me/s/{CHANNEL}",
    f"https://rsshub.app/telegram/channel/{CHANNEL}",
    f"https://tg.i-c-a.su/rss/{CHANNEL}",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def http_get(url, timeout=30):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                print(f"GET {url} -> HTTP {resp.status}", file=sys.stderr)
                return None
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"GET {url} failed: {e}", file=sys.stderr)
        return None


def extract_link(body):
    decoded = (
        body.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
    )
    m = LINK_PATTERN.search(decoded)
    return m.group(0) if m else None


def looks_valid(decoded):
    return bool(re.search(r"(vless|vmess|trojan|ss)://", decoded))


def main():
    for src in SOURCES:
        body = http_get(src)
        if not body:
            continue
        link = extract_link(body)
        if not link:
            continue
        print(f"Found link via {src}: {link}", file=sys.stderr)
        raw = http_get(link)
        if not raw:
            continue
        try:
            decoded = base64.b64decode(raw.strip()).decode("utf-8", errors="ignore")
        except Exception:
            continue
        if looks_valid(decoded):
            with open("mifa.txt", "w") as f:
                f.write(decoded)
            print("Subscription updated successfully", file=sys.stderr)
            return 0
    print("Could not refresh subscription from any source", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
