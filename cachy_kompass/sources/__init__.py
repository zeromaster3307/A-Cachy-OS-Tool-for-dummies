"""Alle unterstützten Installationsquellen.

Die Reihenfolge ist wichtig: ``ManualSource`` muss zuletzt laufen, weil sie
alles überspringt, was eine andere Quelle schon kennt.
"""

from cachy_kompass.sources.base import PackageSource, ScanContext
from cachy_kompass.sources.devtools import BrewSource, CargoSource, NpmSource
from cachy_kompass.sources.files import AppImageSource, ManualSource
from cachy_kompass.sources.flatpak import FlatpakSource
from cachy_kompass.sources.pacman import PacmanSource
from cachy_kompass.sources.python_tools import PipxSource, UvToolSource
from cachy_kompass.sources.snap import SnapSource


def all_sources() -> list[PackageSource]:
    return [
        PacmanSource(),
        FlatpakSource(),
        SnapSource(),
        PipxSource(),
        UvToolSource(),
        CargoSource(),
        NpmSource(),
        BrewSource(),
        AppImageSource(),
        ManualSource(),
    ]


__all__ = ["PackageSource", "ScanContext", "all_sources"]
