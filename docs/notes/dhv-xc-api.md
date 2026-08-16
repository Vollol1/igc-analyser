# dhv-xc.de API / UI Notes

This document describes how `scripts/list_flights.py` authenticates against and
extracts data from [dhv-xc.de](https://www.dhv-xc.de). It is based on code
inspection of the site's `kers.app` JavaScript bundles and live HTTP requests.

## Overview

The dhv-xc.de frontend is a single-page-style application built on top of the
`kers.app` framework. The server renders a small HTML shell that contains:

- a session cookie (`PHPSESSID`)
- an inline JavaScript assignment `jc.token = '<32-char-hex>'` used as a CSRF token
- the bootstrapping call `kers.app.xc.handler.init(...)`

All subsequent interactions (login, flight grids, IGC downloads) happen through
REST-ish endpoints under `/api/...`. The JavaScript bundle is versioned, e.g.
`/v.94a4733/assets/js/kersapp/xc-de.min.js`.

## Authentication

Credentials are supplied to the tool via environment variables or a local
`.env` file:

```bash
DHV_XC_USERNAME=<username or email>
DHV_XC_PASSWORD=<password>
```

No credentials are stored in source code, logs, or the generated JSONL file.

### Login form fields

The HTML login form contains:

- `uid` – username or email address
- `pwd` – password
- `stay` – remember-me checkbox (value `1`)
- `dhvfetch` – hidden flag set to `0` for a normal XC login

The visible login button is a `<button type="button">` bound by JavaScript; the
form itself has no `action` attribute, so the browser does **not** submit it
traditionally.

### CSRF token (`jc.token`)

The token is emitted in the HTML head as:

```html
<script type="text/javascript">
  //<![CDATA[
  ...
  jc.token = 'f78001c3381eff7f88e8f475469cfc59';
  ...
</script>
```

`scripts/list_flights.py` fetches `/login`, extracts `jc.token` with a regex,
and sends it as the HTTP header:

```http
X-Csrf-Token: <token>
```

The kers JavaScript also supports sending the token as a query parameter
(`?token=...`) or in `FormData`. The header is the cleanest variant for an API
client. After a successful login the server may return a refreshed token in the
response `meta.token`; the client updates its stored token accordingly.

### Login endpoint

The kers login model is configured as:

```js
mdl.Login = function () {
    kers.mvc.Model.call(this, 'id', {
        restful: restful,
        serviceController: 'api/xc/login',
        colProps: { id: { type: 'int' } }
    });
};
```

For a RESTful model, executing the action `login` translates to:

```http
POST /api/xc/login/login HTTP/1.1
X-Csrf-Token: <token>
Content-Type: multipart/form-data; boundary=...

uid=<username>&pwd=<password>&stay=1&dhvfetch=0
```

The response is JSON:

```json
{
  "success": true,
  "message": "",
  "meta": { "code": 0, "token": "<optional-new-token>" },
  "data": { ... }
}
```

A failed login returns `success: false` and a descriptive message such as
`Benutzer nicht vorhanden` or `Passwort falsch`.

### DHV service portal login

The site also supports logging in through the DHV service portal
(`service.dhv.de`). This is triggered when:

- the XC account is mapped to a DHV portal user, **or**
- the backend returns the special login result code
  `FAILURE_DHVMAPPING_REQUIRED`.

`scripts/list_flights.py` currently implements the **direct XC login only**.
Users whose account requires the DHV service portal flow must either:

- link / map a DHV portal user in their XC profile once through the web UI, or
- perform the service-portal login manually in a browser and reuse the resulting
  `PHPSESSID` cookie (not yet automated).

No 2FA or CAPTCHA has been observed on the XC login path itself, but the DHV
service portal may introduce additional steps at any time.

## Flight list API

### Endpoint

The flight grid uses the model:

```js
mdl.Flight = function () {
    kers.mvc.Model.call(this, 'IDFlight', {
        restful: restful,
        serviceController: 'api/fli/flights',
        colProps: { IDFlight: { type: 'int' }, ... }
    });
};
```

The corresponding read endpoint is:

```http
GET /api/fli/flights?... HTTP/1.1
X-Csrf-Token: <token>
Accept: application/json
```

### Filters

The UI command `only-mine` sets the filter object to:

```js
{ mine: 1, incpriv: 1 }
```

These are passed as query parameters to the API:

- `mine=1` – show only flights belonging to the authenticated pilot
- `incpriv=1` – include private flights in the result

### Pagination

The kers grid does not use traditional page numbers. It passes `navpars` as a
URL-encoded JSON object containing `start`, `limit`, `sort`, and `dir`:

```text
navpars={"start":0,"limit":50,"sort":"FlightDate","dir":"desc"}
```

`scripts/list_flights.py` loops with increasing `start` until a page returns
fewer rows than the requested limit.

### Response shape

A successful response looks like:

```json
{
  "success": true,
  "message": "",
  "meta": { "total": 350 },
  "data": [
    {
      "IDFlight": 123456,
      "FlightDate": "2025-07-20",
      "FlightDuration": 10800,
      "BestTaskDistance": 78500,
      "TakeoffLocation": "Brauneck",
      "Glider": "Nova Mentor 5 [EN-B]",
      ...
    }
  ]
}
```

## IGC download URL

Each flight detail page offers an IGC download. The canonical URL pattern is:

```text
https://www.dhv-xc.de/flight/{IDFlight}/igc
```

## Field mapping

| JSONL field        | Source field(s) in API row                          | Transformation |
|--------------------|-----------------------------------------------------|----------------|
| `IDFlight`         | `IDFlight`                                          | integer        |
| `FlightDate`       | `FlightDate`                                        | as-is          |
| `TakeoffLocation`  | `TakeoffLocation`, `TakeoffName`, `StartLocation`; fallback `FKTakeoffWaypoint` | string or `FKTakeoffWaypoint:<id>` |
| `Glider`           | `Glider`, `GliderName`; fallback `FKGlider`         | string or `FKGlider:<id>` |
| `BestTaskDistance` | `BestTaskDistance`                                  | meters → km    |
| `FlightDuration`   | `FlightDuration`                                    | seconds → minutes |
| `IgcUrl`           | constructed from `IDFlight`                         | `/flight/{id}/igc` |
| `ExtractedAt`      | generated                                           | UTC ISO-8601   |

## Missing fields in the flight list

The `/api/fli/flights` endpoint (used by the "only mine" / "include private"
grid with filters `mine=1` and `incpriv=1`) does **not** return a landing
location. The response rows contain takeoff, glider, duration and best task
distance, but no `LandingLocation` field.

## Flight detail page: landing location

Although the flight list omits it, the landing location is available on the
individual flight detail page:

```text
GET /flight/<IDFlight>
```

The server-rendered HTML contains an inline `<script>` block that bootstraps the
flight detail handler, e.g.:

```js
kers.app.fli.handler.init({
    ...
    LandingLocation: "Some Landing Place, Region, Country",
    ...
});
```

So `LandingLocation` can be scraped from that initialization object if needed.

### Future extension options

To include `LandingLocation` in the export, one of the following approaches
would work:

1. Enrich in `list_flights.py`:
   - After fetching the flight list, request `/flight/<IDFlight>` for every
     flight.
   - Parse the `kers.app.fli.handler.init(...)` script block and extract
     `LandingLocation`.
   - Add it to the `FlightRecord` / JSONL output.
   - Cost: **one extra HTTP request per flight** and additional rate-limiting /
     retry logic.

2. Lazy enrichment in `export_igc_zip.py`:
   - Keep the JSONL schema as-is.
   - When building the export, optionally query detail pages and add
     `LandingLocation` to the CSV/PDF on demand.
   - Cost: same per-flight request load, but only incurred when an export is
     generated.

Until one of these is implemented, `LandingLocation` is intentionally left
out of the export because the flight list does not provide it reliably.

## Manual interventions / limitations

- **Credentials**: must be provided by the user in `.env` or environment variables.
- **DHV service portal**: not automated. If required, link the accounts via the web UI first.
- **2FA / CAPTCHA**: not currently present on the XC login path; may require script updates if added.
- **API changes**: the site is JavaScript-heavy; endpoint or `jc.token` changes may need adjustments.
- **Rate limiting**: be polite; do not run in a tight loop.

## References

- `kers.app` models in `/v.<hash>/assets/js/kersapp/xc-de.min.js`
  - `serviceController: 'api/xc/login'`
  - `serviceController: 'api/fli/flights'`
  - `serviceController: 'api/geo/waypoints'`
  - `serviceController: 'api/gli/gliders'`
