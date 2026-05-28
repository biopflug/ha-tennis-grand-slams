# Tennis Grand Slams for Home Assistant

Eine Custom Integration für Home Assistant/HACS, die automatisch erkennt:

- welches Tennis-Grand-Slam-Turnier gerade läuft,
- welches Grand Slam als nächstes kommt,
- wie viele Tage es bis dahin sind,
- welche Live-Spiele aktuell zum Grand Slam gefunden werden,
- welche kommenden Spiele anstehen,
- welche Ergebnisse zuletzt gefunden wurden,
- und einen Kalender mit den erkannten Grand-Slam-Zeiträumen bereitstellt.

Die Integration nutzt die öffentlichen ESPN-Tennis-Scoreboard-Daten für ATP und WTA. Diese Endpunkte sind praktisch, aber nicht offiziell als stabile öffentliche API garantiert. Falls ESPN die Struktur ändert, muss die Integration angepasst werden.

## Installation über HACS

1. Dieses Repository auf GitHub hochladen.
2. In Home Assistant: HACS → Integrationen → Drei Punkte → Benutzerdefinierte Repositories.
3. Repository-URL einfügen.
4. Kategorie: `Integration`.
5. `Tennis Grand Slams` installieren.
6. Home Assistant neu starten.
7. Einstellungen → Geräte & Dienste → Integration hinzufügen → `Tennis Grand Slams`.

## Entitäten

Nach der Einrichtung entstehen diese Entitäten:

- `sensor.grand_slam_status`
- `sensor.tage_bis_zum_nachsten_grand_slam`
- `sensor.grand_slam_live_matches`
- `sensor.grand_slam_upcoming_matches`
- `sensor.grand_slam_recent_results`
- `sensor.letzte_espn_aktualisierung`
- `calendar.grand_slam_kalender`

Die genauen Entity-IDs können je nach Sprache/System leicht abweichen. Im Zweifel in Home Assistant unter Einstellungen → Geräte & Dienste → Entitäten nachsehen.

## Dashboard

Eine fertige Dashboard-YAML liegt in:

```text
examples/dashboard.yaml
```

Diese kannst du als manuelle Karte in Lovelace einfügen.

## Was die Integration automatisch macht

Die Integration fragt ATP und WTA über ESPN ab und sucht in den Turnier- bzw. Eventnamen nach:

- Australian Open
- French Open / Roland Garros
- Wimbledon
- US Open

Daraus werden die Grand-Slam-Zeiträume, das aktuelle bzw. nächste Grand Slam und die passenden Matches abgeleitet.

## Optionen

In der Integration kannst du einstellen:

- Region, Standard: `de`
- Sprache, Standard: `de`
- Suchzeitraum in Tagen, Standard: `420`
- Aktualisierungsintervall in Minuten, Standard: `15`

## Hinweise

Diese Integration verändert dein Dashboard nicht automatisch. Home Assistant/HACS-Integrationen sollten nicht ungefragt Lovelace-Karten anlegen. Deshalb liegt die Dashboard-Konfiguration als Beispiel-Datei bei.
