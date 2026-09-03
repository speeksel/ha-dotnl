# DOT-NL publieke laadpalen (Home Assistant integration)

Home Assistant custom integration die **openbare laadpalen in een zelf te kiezen
gebied** monitort via de [DOT-NL (DAFNE) API van NDW](https://docs.ndw.nu/data-uitwisseling/interface-beschrijvingen/dafne-api/).

Per laadpaal worden entiteiten aangemaakt die direct bruikbaar zijn in
automations en dashboards:

| Entiteit | Type | Betekenis |
|---|---|---|
| `binary_sensor.*_beschikbaar` | Binary sensor | **Aan** = minstens één aansluiting vrij |
| `sensor.*_vrije_aansluitingen` | Sensor | Aantal vrije aansluitingen |
| `sensor.*_totaal_aansluitingen` | Sensor | Totaal aantal aansluitingen (diagnostisch) |

De binary sensor draagt als attributen o.a. het adres, de exploitant, de
coördinaten, de laatste update-timestamp en per connector het type, vermogen en
de bezetting mee.

## Installatie (HACS)

1. Zorg dat [HACS](https://hacs.xyz) geïnstalleerd is.
2. HACS → ⋮ → **Custom repositories** → voeg deze repository toe met categorie
   *Integration*.
3. HACS → zoek **"DOT-NL Laadpalen"** → download.
4. Herstart Home Assistant.

Alternatief zonder HACS: kopieer `custom_components/dotnl/` naar de
`custom_components/`-map van je Home Assistant-configuratie en herstart.

## Configuratie

1. **Instellingen → Apparaten & Diensten → Integratie toevoegen** →
   zoek **"DOT-NL Laadpalen"**.
2. Teken op [bboxfinder.com](https://bboxfinder.com) het gewenste gebied en
   noteer de coördinaten (lon/lat, decimalen).
3. Vul in:
   - **Naam van het gebied** — bijvoorbeeld `Zuid-Leeuwarden`
   - **Minimum lengtegraad** (west) en **minimum breedtegraad** (zuid)
   - **Maximum lengtegraad** (oost) en **maximum breedtegraad** (noord)
   - **Verversingsinterval** — seconden tussen polls (standaard 60, min. 30)
4. De integratie test het gebied direct: hij weigert gebieden groter dan
   **1,0 vierkante graad** (API-limiet) en gebieden zonder laadpalen.

Je kunt meerdere gebieden toevoegen (elk wordt een eigen config entry met
eigen polling-coordinator). Wijzigen kan via **Reconfigure** op de integratie.

> Voorbeeld — Zuid-Leeuwarden:
> `min_lon=5.755, min_lat=53.208, max_lon=5.795, max_lat=53.222` (33 laadpalen)

## Automation-voorbeeld: melding als een laadpaal vrijkomt

```yaml
alias: "Laadpaal De Jokse 586 beschikbaar"
description: "Stuur een melding zodra er een aansluiting vrijkomt"
trigger:
  - platform: state
    entity_id: binary_sensor.de_jokse_586_beschikbaar
    from: "off"
    to: "on"
action:
  - service: notify.mobile_app_mijn_telefoon
    data:
      title: "Laadpaal vrij"
      message: "Laadpaal De Jokse 586 (Allego) heeft weer een vrije aansluiting!"
mode: single
```

## Dashboard-voorbeeld (YAML)

```yaml
type: entities
title: Laadpaal De Jokse 586
entities:
  - entity: binary_sensor.de_jokse_586_beschikbaar
  - entity: sensor.de_jokse_586_vrije_aansluitingen
  - entity: sensor.de_jokse_586_totaal_aansluitingen
```

## API-limieten & aandachtspunten

- Maximaal **1,0 vierkante graad** per gebied en **1000 laadpalen** per request
  (API-limiet van DOT-NL). Kies je gebied dus niet te groot; gebruik anders
  meerdere config entries.
- Maximaal **10 requests per seconde** — bij meerdere gebieden met een korte
  poll-interval kun je hier tegenaan lopen (HTTP 429). De integratie laat dit
  als fout in de logboek zien.
- De dynamische feed toont **aantallen** (`beschikbaar/totaal`) en het adres.
  Het onderscheid *bezet door een auto* vs. *defect/geblokkeerd* zit alleen in
  de volledige OCPI-bulkdataset, niet in deze realtime API.
- Nieuwe laadpalen die later in het gebied verschijnen verschijnen pas na een
  herlaad van de integratie (Reconfigure).

## Licentie

MIT
