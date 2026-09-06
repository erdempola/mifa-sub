#!/usr/bin/env python3
import re
import sys
import os
import time
import glob
import base64
import datetime
import urllib.request

CHANNEL = "mifa_world"
# Постоянная ссылка на редактируемый ежедневно пост с промо-линком —
# содержимое лежит в <meta property="og:description">, отдаётся статически,
# не зависит от общего веб-превью канала (t.me/s/...), которое MIFA иногда отключает.
PERMALINK = f"https://t.me/{CHANNEL}/1310/27737"
LINK_PATTERN = re.compile(r"https?://mifa\.world/[a-zA-Z0-9/_-]+")
OG_DESC_PATTERN = re.compile(r'<meta property="og:description" content="(.*?)">', re.DOTALL)
SOURCES = [
    f"https://t.me/s/{CHANNEL}",
    f"https://telegram.me/s/{CHANNEL}",
    f"https://rsshub.app/telegram/channel/{CHANNEL}",
    f"https://tg.i-c-a.su/rss/{CHANNEL}",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def http_get(url, timeout=30, retries=2, retry_delay=4):
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status != 200:
                    print(f"GET {url} -> HTTP {resp.status} (попытка {attempt}/{retries})", file=sys.stderr)
                    last_err = f"HTTP {resp.status}"
                else:
                    return resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"GET {url} failed: {e} (попытка {attempt}/{retries})", file=sys.stderr)
            last_err = str(e)
        if attempt < retries:
            time.sleep(retry_delay)
    return None


def extract_link_from_permalink(html):
    m = OG_DESC_PATTERN.search(html)
    if not m:
        return None
    text = (
        m.group(1)
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    m2 = LINK_PATTERN.search(text)
    return m2.group(0) if m2 else None


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


CHUNK_SIZE = 99


def write_full_file(lines, now, total):
    header = f"# Date/Time: {now}\n# Количество: {total}\n"
    with open("mifa.txt", "w") as f:
        f.write(header + "\n".join(lines) + "\n")


def write_chunks(lines, now, total):
    # убираем старые куски, чтобы не оставалось "хвостов" от прошлого запуска
    for old in glob.glob("mifa[0-9]*.txt"):
        os.remove(old)

    chunks = [lines[i:i + CHUNK_SIZE] for i in range(0, len(lines), CHUNK_SIZE)]
    for idx, chunk in enumerate(chunks, start=1):
        header = (
            f"# Date/Time: {now}\n"
            f"# Часть {idx}/{len(chunks)}, узлов в этой части: {len(chunk)} (всего: {total})\n"
        )
        with open(f"mifa{idx}.txt", "w") as f:
            f.write(header + "\n".join(chunk) + "\n")
    return len(chunks)


def find_fresh_link():
    # Основной способ: постоянная ссылка на пост, содержимое в og:description.
    html = http_get(PERMALINK)
    if html:
        link = extract_link_from_permalink(html)
        if link:
            print(f"Found link via permalink {PERMALINK}: {link}", file=sys.stderr)
            return link
        print("Permalink ответил, но ссылка mifa.world не найдена в og:description", file=sys.stderr)

    # Запасной вариант: старые мосты (менее надёжные, могут банить IP или зависеть от /s/-виджета).
    for src in SOURCES:
        body = http_get(src)
        if not body:
            continue
        link = extract_link(body)
        if link:
            print(f"Found link via {src}: {link}", file=sys.stderr)
            return link
    return None


def main():
    link = find_fresh_link()
    if link:
        raw = http_get(link)
        if raw:
            try:
                decoded = base64.b64decode(raw.strip()).decode("utf-8", errors="ignore")
            except Exception:
                decoded = None
            if decoded and looks_valid(decoded):
                lines = [l for l in decoded.strip().split("\n") if l.strip()]
                now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).strftime("%Y-%m-%d / %H:%M MSK")
                write_full_file(lines, now, len(lines))
                n_chunks = write_chunks(lines, now, len(lines))
                print(f"Subscription updated successfully: {len(lines)} nodes in {n_chunks} chunk file(s)", file=sys.stderr)
                return 0
    print("Could not refresh subscription from any source", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
