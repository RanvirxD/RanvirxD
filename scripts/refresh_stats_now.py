#!/usr/bin/env python3
"""Regenerate stat SVGs from live public GitHub data (no token required)."""
import json
import os
import sys
import urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from generate_stats import (
    draw_heading,
    draw_langs,
    draw_stats,
    draw_streak,
    draw_year,
    streaks,
    write,
)

LOGIN = os.environ.get("GH_LOGIN", "RanvirxD")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": f"{LOGIN}-profile-stats"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_contributions(login):
    data = get(f"https://github-contributions-api.jogruber.de/v4/{login}?y=last")
    weeks, days = [], []
    for i in range(0, len(data["contributions"]), 7):
        week = []
        for c in data["contributions"][i : i + 7]:
            dt = datetime.strptime(c["date"], "%Y-%m-%d")
            day = {
                "date": c["date"],
                "contributionCount": c["count"],
                "weekday": (dt.weekday() + 1) % 7,
            }
            week.append(day)
            days.append(day)
        weeks.append(week)
    return days, weeks


def fetch_languages(login):
    repos = get(f"https://api.github.com/users/{login}/repos?per_page=100&type=owner&sort=updated")
    by_size, by_repo = {}, {}
    for repo in repos:
        if repo.get("fork"):
            continue
        try:
            langs = get(repo["languages_url"])
        except Exception:
            continue
        edges = sorted(langs.items(), key=lambda kv: -kv[1])
        for name, size in langs.items():
            by_size[name] = by_size.get(name, 0) + size
        if edges:
            top = edges[0][0]
            by_repo[top] = by_repo.get(top, 0) + 1

    def rank(d):
        return sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))[:5]

    return rank(by_size), rank(by_repo)


def main():
    days, weeks = fetch_contributions(LOGIN)
    weekly = [sum(d["contributionCount"] for d in w) for w in weeks]
    cur, best = streaks(days)
    by_size, by_repo = fetch_languages(LOGIN)
    s = dict(
        total=sum(d["contributionCount"] for d in days),
        active=sum(1 for d in days if d["contributionCount"] > 0),
        best_week=max(weekly) if weekly else 0,
        weekly=weekly,
        weeks=weeks,
        current=cur,
        longest=best,
        by_size=by_size,
        by_repo=by_repo,
    )
    files = {
        "stats.svg": draw_stats(s),
        "streak.svg": draw_streak(s),
        "langs.svg": draw_langs(s),
        "year.svg": draw_year(s),
    }
    for word in ("about", "stack", "projects", "stats", "about this page"):
        files[f"hd-{word.replace(' ', '-')}.svg"] = draw_heading(word)

    changed = []
    for name, svg in files.items():
        if write(os.path.join(ROOT, name), svg):
            changed.append(name)

    print(
        f"{s['total']} contributions, {s['active']} active days, "
        f"best week {s['best_week']}, current streak {s['current']['length']}, "
        f"longest streak {s['longest']['length']}"
    )
    print("languages by bytes: " + ", ".join(f"{n} {v}" for n, v in s["by_size"]))
    print("updated: " + (", ".join(sorted(changed)) if changed else "nothing"))


if __name__ == "__main__":
    main()
