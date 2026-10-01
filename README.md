# Business Central Dashboard

Een Flask-dashboard voor operationele informatie uit Microsoft Dynamics 365 Business Central. Het dashboard toont order- en verzendinformatie en heeft drie kioskweergaven. De derde kioskweergave toont daarnaast de agenda van een Microsoft 365-mailbox.

## Functionaliteit

- Overzicht van toekomstige leverweken, orders en colli.
- Detailoverzicht per leverweek.
- Overzicht van hoofdorders en meeliftorders.
- Overzicht van verzonden orders en magazijnzendingen.
- Kioskweergaven voor schermen op de werkvloer.
- Werkagenda voor de huidige werkweek in de derde kioskweergave.

## Benodigdheden

- Python 3.10 of nieuwer
- Toegang tot de Business Central API
- Optioneel: een Microsoft Graph-applicatie met toegang tot de agenda-mailbox

Installeer de Python-pakketten in een virtuele omgeving:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install Flask pandas python-dotenv msal requests
```

Op Windows kan het activeren van een virtuele omgeving door PowerShell-beleid worden geblokkeerd. Voer in dat geval de commando's uit via een terminal waarin de omgeving al is geactiveerd, of gebruik rechtstreeks `.venv\Scripts\python.exe`.

## Configuratie

Maak in de projectmap een bestand met de naam `.env`. Gebruik geen aanhalingstekens tenzij die onderdeel zijn van de waarde.

### Business Central

Deze waarden zijn nodig voor het ophalen van sales headers:

```dotenv
api_client_id=...
api_client_secret=...
api_tenant_id=...
api_company_id=...
api_environment=PROD
```

De gebruikte endpoint is de custom Business Central API `schipper/verver/v1.0`, met de entity `salesHeaders`. De Azure-applicatie moet daarvoor een client-credentials-token kunnen ophalen en toegang hebben tot de betreffende Business Central-omgeving en company.

### Microsoft Graph-agenda

Deze waarden zijn alleen nodig voor `/kiosk/display-3`:

```dotenv
client_id_calendar=...
client_secret_calendar=...
tenant_id_calendar=...
mailbox_calendar=agenda@example.com
```

De Graph-applicatie moet applicatietoegang hebben tot `https://graph.microsoft.com/.default` en agenda's kunnen lezen voor de opgegeven mailbox. Zonder deze configuratie werken de orderpagina's wel, maar de agenda-kiosk niet.

### Flask-server

```dotenv
host=127.0.0.1
port=5000
```

Gebruik voor toegang vanaf andere apparaten op hetzelfde netwerk bijvoorbeeld `host=0.0.0.0`. Beveilig de server en netwerktoegang wanneer hij buiten de lokale computer beschikbaar wordt gemaakt.

## Data ophalen

Start het ophalen van Business Central-data in een aparte terminal:

```powershell
python api_caller.py
```

Dit proces haalt standaard de leverweken van één week geleden tot en met acht weken vooruit op, schrijft de resultaten naar `salesHeaders.json` en herhaalt dit iedere vijf minuten. Het proces blijft actief totdat het wordt gestopt met `Ctrl+C`.

De Flask-app leest `salesHeaders.json` bij ieder dashboardverzoek. Zorg daarom dat `api_caller.py` minstens één keer succesvol heeft gedraaid voordat je het dashboard opent.

## Dashboard starten

Start in een tweede terminal:

```powershell
python dashboard.py
```

Open daarna:

| Pagina | URL |
| --- | --- |
| Dashboard | `http://127.0.0.1:5000/dashboard` |
| Weekoverzicht | `http://127.0.0.1:5000/dashboard/week-<weeknummer>` |
| Hoofdorders | `http://127.0.0.1:5000/dashboard/hoofdorders/<weeknummer>` |
| Verzendingen | `http://127.0.0.1:5000/verzendingen` |
| Kiosk 1 | `http://127.0.0.1:5000/kiosk/display-1` |
| Kiosk 2 | `http://127.0.0.1:5000/kiosk/display-2` |
| Kiosk 3: agenda | `http://127.0.0.1:5000/kiosk/display-3` |

De root-URL `/` verwijst automatisch door naar `/dashboard`.

## Projectstructuur

```text
dashboard.py             Flask-routes en dashboardlogica
api_caller.py            Business Central-data ophalen en lokaal opslaan
accesstoken.py           Business Central OAuth2-client credentials
get_calendar.py          Agenda-events ophalen via Microsoft Graph
_acces_token_calendar.py Microsoft Graph OAuth2-client credentials
salesHeaders.json        Lokale API-cache (wordt gegenereerd)
templates/               Jinja2-templates voor de pagina's
static/                  CSS en overige statische bestanden
```

## Veiligheid en onderhoud

- Commit nooit `.env`, client secrets, access tokens of gegenereerde API-data.
- `*.json` staat in `.gitignore`; voeg alleen JSON-bestanden toe aan Git als dat bewust nodig is.
- Zet `debug=False` en gebruik een productiegerichte WSGI-server wanneer het dashboard wordt gedeployed.
- De applicatie gebruikt de timestamp uit `salesHeaders.json` om de laatste succesvolle data-update te tonen.

## Problemen oplossen

- **503 op het dashboard:** `salesHeaders.json` ontbreekt of bevat ongeldige JSON. Start `python api_caller.py` en controleer de Business Central-configuratie.
- **Tokenfout:** controleer de client-id, secret, tenant-id en de rechten van de Azure-applicatie.
- **Agenda werkt niet:** controleer de Graph-variabelen, `mailbox_calendar` en de agenda-rechten van de Graph-applicatie.
- **Poort al in gebruik:** kies een andere waarde voor `port` in `.env` en gebruik die poort ook in de browser-URL.

