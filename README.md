# RAPP — kody-w.com

Static landing page for the **RAPP stack**, served from this repo via GitHub Pages at [kody-w.com](https://kody-w.com).

The page is a digital twin of the three-tier RAPP architecture:

1. **🧠 Brainstem** — local Flask server, GitHub Copilot LLM
2. **☁️ Hippocampus (CommunityRAPP)** — Azure Functions + Azure OpenAI
3. **🤖 Copilot Studio Harness** — Power Platform `.zip` solution

All install commands and links resolve to the canonical sources:

- [kody-w/rapp-installer](https://github.com/kody-w/rapp-installer) — brainstem + cloud installers + Copilot Studio `.zip`
- [kody-w/CommunityRAPP](https://github.com/kody-w/CommunityRAPP) — Tier 2 cloud project template

## Files

| File | Purpose |
|---|---|
| `index.html` | The landing page (vanilla HTML/CSS/JS, zero deps) |
| `CNAME` | Custom domain config (`kody-w.com`) |
| `.nojekyll` | Tell Pages to serve files as-is |

## Deploy

GitHub Pages → Settings → Pages → Source: `main` branch, root.
The custom domain `kody-w.com` is set via `CNAME`.

## History

The previous engine code that lived in this repo (Rapp intelligence engine for Rappterbook) is preserved on the `archive/engine` branch.
