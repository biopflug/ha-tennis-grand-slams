# Tennis Grand Slams for Home Assistant

Custom Integration für Home Assistant/HACS.

Version 0.1.5 nutzt mehrere Fallbacks:

- ESPN Site API Scoreboard für ATP/WTA
- ESPN Tournament Pages als HTML-Fallback, falls die API nur Turnier-Shells liefert
- eingebaute Grand-Slam-Kalenderlogik für aktuelles/nächstes Turnier

Die ESPN-Endpunkte sind nicht offiziell als stabile öffentliche API garantiert. Wenn ESPN die Struktur ändert oder HTML/Bot-Schutz ausliefert, muss der Parser angepasst werden.

## Installation über HACS

1. Repository auf GitHub hochladen.
2. HACS → Integrationen → Benutzerdefinierte Repositories.
3. Repository-URL einfügen, Kategorie `Integration`.
4. Installieren und Home Assistant neu starten.
5. Einstellungen → Geräte & Dienste → `Tennis Grand Slams` hinzufügen.

## Dashboard

Eine Beispielkarte liegt in `examples/dashboard.yaml`.

## Debug

Der Status-Sensor enthält ein `debug`-Attribut. Wichtig sind:

- `raw_events`: Anzahl ESPN-API-Rohdaten
- `parsed_matches`: daraus gelesene Matchdaten
- `page_matches`: über ESPN-Turnierseiten gescrapte Matches
- `raw_event_samples`: kurze Strukturbeispiele für weitere Fehleranalyse
