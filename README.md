# Tennis Grand Slams for Home Assistant

Custom Integration fuer Home Assistant/HACS.

Version 0.2.0 liefert Sensoren, Kalenderdaten und eine Lovelace Custom Card fuer ein Grand-Slam-Dashboard:

- aktueller oder naechster Grand Slam mit Zeitraum und Ort
- Startdatum des naechsten Grand Slams
- heutige Grand-Slam-Matches
- Live Matches
- kommende Matches und letzte Ergebnisse
- klickbare Match-Zeilen mit Uhrzeit, Status, aktuellem Spielstand, Satzdetails und ESPN-Link

Die ESPN-Endpunkte sind nicht offiziell als stabile oeffentliche API garantiert. Wenn ESPN die Struktur aendert oder HTML/Bot-Schutz ausliefert, muss der Parser angepasst werden.

## Installation ueber HACS

1. Repository auf GitHub hochladen.
2. HACS -> Integrationen -> Benutzerdefinierte Repositories.
3. Repository-URL einfuegen, Kategorie `Integration`.
4. Installieren und Home Assistant neu starten.
5. Einstellungen -> Geraete & Dienste -> `Tennis Grand Slams` hinzufuegen.

## Dashboard Card

Die Integration stellt die Lovelace-Ressource nach dem Laden unter dieser URL bereit:

```text
/tennis_grand_slams/frontend/tennis-grand-slam-card.js
```

In Home Assistant unter Einstellungen -> Dashboards -> Ressourcen als `JavaScript module` eintragen.

Danach kann die Karte aus `examples/dashboard.yaml` in ein Dashboard eingefuegt werden:

```yaml
type: custom:tennis-grand-slam-card
status_entity: sensor.tennis_grand_slams_grand_slam_status
today_entity: sensor.tennis_grand_slams_grand_slam_today_matches
live_entity: sensor.tennis_grand_slams_grand_slam_live_matches
upcoming_entity: sensor.tennis_grand_slams_grand_slam_upcoming_matches
results_entity: sensor.tennis_grand_slams_grand_slam_recent_results
max_matches: 14
show_recent_results: true
```

## Entitaeten

- `sensor.tennis_grand_slams_grand_slam_status`
- `sensor.tennis_grand_slams_tage_bis_zum_nachsten_grand_slam`
- `sensor.tennis_grand_slams_grand_slam_today_matches`
- `sensor.tennis_grand_slams_grand_slam_live_matches`
- `sensor.tennis_grand_slams_grand_slam_upcoming_matches`
- `sensor.tennis_grand_slams_grand_slam_recent_results`
- `sensor.tennis_grand_slams_letzte_espn_aktualisierung`
- `calendar.tennis_grand_slams_grand_slam_kalender`

## Debug

Der Status-Sensor enthaelt ein `debug`-Attribut. Wichtig sind:

- `raw_events`: Anzahl ESPN-API-Rohdaten
- `parsed_matches`: daraus gelesene Matchdaten
- `today_matches`: erkannte Matches fuer den heutigen Tag in der Home-Assistant-Zeitzone
- `page_matches`: ueber ESPN-Turnierseiten gescrapte Matches
- `raw_event_samples`: kurze Strukturbeispiele fuer weitere Fehleranalyse
