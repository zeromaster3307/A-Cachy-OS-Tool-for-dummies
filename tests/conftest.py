"""Die Tests prüfen deutsche Texte – deshalb immer auf Deutsch laufen, egal welche Systemsprache.

Muss vor dem ersten Import von ``cachy_kompass`` passieren, weil manche Texte
schon beim Laden der Module übersetzt werden.
"""

import os

os.environ["CACHY_KOMPASS_LANG"] = "de"
