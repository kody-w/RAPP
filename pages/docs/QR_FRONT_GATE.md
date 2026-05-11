# Front Gate Trio — QR + Holocard + Incantation (Mandatory)

**Status:** mandatory as of 2026-05-11.
**Schema:** `rapp-front-gate-qr/1.0` (QR) + `rapp-card/1.1.2` (holocard) + `rapp-front-gate-incantation/1.0` (incantation).
**Spec layer:** ECOSYSTEM_MAP §6 (Implementation map) — bound under Article XLVII (substrate-agnostic federation) and Article LI (front-gate mandates).

## Three summoning surfaces, one front gate

Every planted neighborhood (and operator twin) front gate surfaces THREE redundant ways to dial in:

1. **QR code** — point a camera at it (scan from any tether).
2. **Holocard** — visual card identity rendered from `card.json` (recognition + provenance at a glance).
3. **7-word incantation** — memorable mnemonic derived from the rappid's first 64 bits via 10-bits-per-word against the 1024-word `MNEMONIC_WORDS` dictionary (spin into any tether's Dial wheel; no network needed for resolution itself).

All three resolve to the same rappid. The QR is for casual visitors with cameras; the holocard is for recognition and provenance; the incantation is the hero use case — memorize 7 words, summon anywhere.

---

## The rule

> **Every neighborhood's planted front gate (`index.html` at the repo root, served via GitHub Pages or any other substrate) MUST display a tether QR code on first paint. The QR is the neighborhood's phone number — any tether scans it to dial in.**

A neighborhood without a visible front-gate QR is non-conforming and will be flagged by the federation roll-up's lint pass (planned). Casual operators can't dial what they can't scan; the QR is the public on-ramp.

---

## What the QR must encode

A URL that resolves to enough information for any tether to tether to this neighborhood.

**Preferred** (covers both server brainstems and browser tethers via smart-unwrap):

```
https://<host>/<repo>/.well-known/neighborhood.egg
```

The egg is a `brainstem-egg/2.3-neighborhood` JSON invite carrying `rappid` + canonical URLs (`neighborhood_json`, `tether_url`, `homepage`). The tether scans → fetches the egg → reads `neighborhood_json` → loads the manifest → hot-loads `tether_requirements.agents`. A server-side brainstem reads the same egg via `@rapp/egg_hatcher` → joins via two-tier estate per Article XLVI.

**Acceptable** (manifest-direct):

```
https://<host>/<repo>/neighborhood.json
```

Lighter; works only for the tether path (no server-side hatch flow).

---

## Canonical drop-in snippet

Every neighborhood's `index.html` should include this. Place the canvas wherever in the layout makes sense; place the script anywhere after the canvas. The snippet auto-detects the deploy URL via `location.origin + location.pathname`, so the same code works whether the neighborhood is at `kody-w.github.io/rapp-commons` or `alice.github.io/her-neighborhood` or `file:///path/to/clone`.

```html
<!-- ╭─── RAPP Front-Gate QR (rapp-front-gate-qr/1.0) ───────────────╮ -->
<canvas id="rapp-front-gate-qr"
        style="background:#fff;padding:8px;border-radius:8px;display:block"
        aria-label="Tether QR for this neighborhood"></canvas>
<script src="https://cdn.jsdelivr.net/npm/qrious@4.0.2/dist/qrious.min.js"></script>
<script>
(function() {
  var el = document.getElementById('rapp-front-gate-qr');
  if (!el) return;
  var base = (location.origin && location.origin !== 'null'
                ? location.origin + location.pathname.replace(/\/[^/]*$/, '')
                : '');
  var url = (base ? base : '.') + '/.well-known/neighborhood.egg';
  if (typeof QRious === 'undefined') {
    // CDN unreachable (offline / file:// with no internet).
    // Degrade by showing the URL plainly so the operator can copy it
    // into a tether's Paste mode.
    el.outerHTML =
      '<div style="background:#fff;color:#000;padding:12px;border-radius:8px;' +
      'font-family:monospace;font-size:0.72rem;text-align:center;word-break:break-all">' +
      'QRious unavailable (offline). Paste this into any tether:<br><br><b>' +
      url + '</b></div>';
    return;
  }
  new QRious({
    element:    el,
    value:      url,
    size:       256,
    background: '#ffffff',
    foreground: '#000000',
    level:      'M'
  });
})();
</script>
<!-- ╰────────────────────────────────────────────────────────────────╯ -->
```

### Notes on the snippet

- **`location.origin` + `pathname` trick** — the snippet auto-detects which deploy it's running in, so the same HTML file works in *any* neighborhood that drops it into their `index.html`. No hardcoding required.
- **`file://` fallback** — `location.origin === 'null'` for `file://` URLs. Snippet falls back to a relative-path URL (`./.well-known/neighborhood.egg`) so a local clone still produces a working QR when opened directly from disk.
- **Graceful degrade** — if QRious can't load (no CDN, offline), the canvas is replaced with the plain URL so the operator can still copy/paste into a tether's Paste mode.
- **Size `256`** — recommended minimum for reliable phone-camera reads from across a room. Smaller may be acceptable for laptop-to-phone use.
- **Error level `M`** — 15% redundancy, balances density vs scannability for typical neighborhood URLs (~60-80 ASCII chars).

---

## What a conforming front gate looks like

A minimum-viable conforming neighborhood `index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>My Neighborhood</title>
</head>
<body>
  <h1>My Neighborhood</h1>
  <p>One-sentence description of what this neighborhood is for.</p>

  <h2>Tether to this neighborhood</h2>
  <!-- (drop-in snippet from above) -->
  <canvas id="rapp-front-gate-qr"></canvas>
  <script src="https://cdn.jsdelivr.net/npm/qrious@4.0.2/dist/qrious.min.js"></script>
  <script>(function(){ /* ... same as snippet above ... */ })();</script>

  <p>
    Open any RAPP tether
    (<a href="https://kody-w.github.io/RAPP/pages/tether.html">public payphone</a>)
    and scan the QR, or paste the URL it encodes into the tether's Paste mode.
  </p>
</body>
</html>
```

The richer commons example at `kody-w/rapp-commons/index.html` adds branding, step-by-step join flow, member counters, and a town-square coordinate explainer — but the *only* mandatory piece is the QR.

---

## The reverse contract — what every tether must support

Any tether that claims to dial neighborhoods MUST handle a scanned QR whose payload is:

1. **An `.egg` URL** (preferred) — fetch the JSON, read `neighborhood_json` (or `neighborhood_url` as fallback), then continue as if that URL were the scan.
2. **A `neighborhood.json` URL** — load directly as the manifest.
3. **A bare URL with `?neighborhood=<URL>` or `?egg=<URL>` query params** — extract the param and resolve as above.

The `tether.html` at `kody-w/RAPP/pages/tether.html` implements all three (see `setNeighborhoodUrl` and `resolveNeighborhoodUrl` in that file). Other tethers should match.

---

## Why this is mandatory

The tether is universal (any deployment, any repo). The neighborhood is the destination. The QR is the visual phone number connecting them. Without the QR on every front gate:

- Casual visitors have no on-ramp — they'd need to manually find and paste the URL.
- The "scan a poster on the wall to join a neighborhood" hero use case (`HERO_USECASE.md`) is broken.
- Substrate-agnostic federation (Article XLVII) loses its visible handoff point.

Making this mandatory ensures the network's public on-ramps stay uniformly accessible.

---

## Conformance check

A neighborhood's front gate conforms if:

1. `index.html` (or equivalent landing page) renders the QR on first paint (no user interaction required).
2. The QR encodes one of the URL formats above.
3. The page degrades gracefully (shows the URL plainly) when QRious can't load.

The federation roll-up's lint pass (planned) will flag non-conforming gates with a `front-gate-qr-missing` warning in the neighborhood's `rar/index.json`.

---

## Migration for existing planted neighborhoods

If you planted a neighborhood before 2026-05-11 without a front-gate QR:

1. Copy the canonical snippet above into your `index.html` (anywhere in the body where the canvas should appear).
2. Push.
3. Wait for GitHub Pages to rebuild.

Done. No other changes required — the snippet auto-detects your deploy URL.
