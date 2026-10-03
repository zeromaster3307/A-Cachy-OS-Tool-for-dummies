"""Doppelt installierte Programme finden.

Nach Anleitungen aus dem Internet landet ein Programm gern zweimal auf dem
Rechner, z. B. Firefox aus dem Repo und zusätzlich als Flatpak, oder yt-dlp
über pacman und zusätzlich über pipx. Das kostet Platz und sorgt für
Verwirrung, welche Version eigentlich startet.

Erkannt wird über vereinfachte Namen: „org.mozilla.firefox“ (Flatpak),
„firefox“ (Repo) und „Firefox-128.0.AppImage“ ergeben alle „firefox“.
"""

from __future__ import annotations

import re

from cachy_kompass.models import Program, Source

# Namenszusätze, die nur die Paketvariante beschreiben
_SUFFIXES = ("-bin", "-git", "-appimage", "-stable", "-desktop", "-browser", "-nightly", "-beta", "-latest")


def name_keys(p: Program) -> set[str]:
    """Vereinfachte Namen, unter denen ein Programm verglichen wird."""
    raw = {p.name}
    if p.source is Source.FLATPAK:
        raw.add(p.name.rsplit(".", 1)[-1])  # org.mozilla.firefox → firefox
    if p.display_name and p.display_name != p.name:
        raw.add(p.display_name)
    keys = set()
    for name in raw:
        key = name.lower().strip()
        for suffix in _SUFFIXES:
            key = key.removesuffix(suffix)
        key = re.sub(r"[\s_.]+", "-", key).strip("-")
        if len(key) >= 3:  # sehr kurze Namen („go“, „qt“) führen zu falschen Treffern
            keys.add(key)
    return keys


def find_duplicates(programs: list[Program]) -> list[list[Program]]:
    """Gruppen von Programmen, die vermutlich dasselbe sind, aber aus verschiedenen Quellen.

    Setzt außerdem ``Program.duplicates`` bei allen Betroffenen.
    """
    candidates = [p for p in programs if p.explicit]
    by_key: dict[str, list[Program]] = {}
    for p in candidates:
        p.duplicates = []
        for key in name_keys(p):
            by_key.setdefault(key, []).append(p)

    groups: list[list[Program]] = []
    seen: set[int] = set()
    for members in by_key.values():
        # pacman-Pakete (Repo/AUR) können nicht doppelt unter gleichem Namen installiert sein;
        # verschiedene Quellen sind das Kennzeichen eines echten Doppels.
        if len({m.source for m in members}) < 2:
            continue
        group_ids = frozenset(id(m) for m in members)
        if group_ids & seen:
            # schon in einer anderen Gruppe – zusammenführen statt doppelt melden
            for g in groups:
                if group_ids & {id(m) for m in g}:
                    g.extend(m for m in members if all(m is not x for x in g))
            seen |= group_ids
            continue
        seen |= group_ids
        groups.append(list(members))

    for g in groups:
        for p in g:
            p.duplicates = [o for o in g if o is not p]
    return groups
