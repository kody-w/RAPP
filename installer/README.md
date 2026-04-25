# `installer/` — Public install surface

The set of files a user downloads, curl-pipes, or imports to get RAPP
running. Every file in `installer/` has a stable public URL of the
shape `https://kody-w.github.io/RAPP/installer/<file>` — that URL is
the contract.

## What's here

### One-liner installers (Tier 1 — Local Brainstem)

| File | Purpose | Public URL pattern |
|---|---|---|
| `install.sh` | macOS/Linux one-liner | `…/installer/install.sh` |
| `install.ps1` | Windows PowerShell one-liner | `…/installer/install.ps1` |
| `install.cmd` | Windows cmd shim that calls `install.ps1` | `…/installer/install.cmd` |
| `start-local.sh` | Local launcher — starts brainstem + opens browser | `…/installer/start-local.sh` |

### Tier 2 — Cloud Swarm

| File | Purpose |
|---|---|
| `install-swarm.sh` | Provisioning one-liner for the Azure Functions deployment |
| `azuredeploy.json` | ARM template — referenced by the Deploy-to-Azure button |

### Tier 3 — Microsoft Copilot Studio

| File | Purpose |
|---|---|
| `MSFTAIBASMultiAgentCopilot_1_0_0_5.zip` | Power Platform solution package — the customer downloads this and imports it into their Copilot Studio tenant |

### Install-widget mirror

| File | Purpose |
|---|---|
| `index.html` | The user-facing install page at `https://kody-w.github.io/RAPP/installer/`. Renders the one-liners as copyable commands and links to the Tier 3 download. |

## What belongs here

A file belongs in `installer/` when it satisfies **both**:

1. **It is the unit of install or download.** A user is meant to
   `curl … | bash`, `irm … | iex`, click *Deploy to Azure*, or
   download-and-import this file. Not source code that builds into
   something else — the file *is* the thing.
2. **Its public URL is part of the contract.** The path
   `https://kody-w.github.io/RAPP/installer/<file>` is referenced in
   `README.md`, the docs, the install widget, vault notes, and
   external partner conversations. Moving or renaming requires
   updating every one of those references.

## What does NOT belong here

- ❌ **Tier-internal source code.** Anything that runs *inside* the
  brainstem or swarm lives in `rapp_brainstem/` or `rapp_swarm/`.
  `installer/` is the surface that bootstraps those, not the code
  itself.
- ❌ **Marketing or audience HTML.** Even if it's about installing
  RAPP, audience-shaped HTML belongs in `pages/`. The widget
  (`installer/index.html`) is here only because it serves the
  `installer/` URL directly and is the operational landing of the
  install surface, not a piece of marketing.
- ❌ **Auxiliary scripts that aren't user-facing.** Internal helper
  scripts (build, vendor, deploy used by other scripts) live in
  the relevant tier directory (e.g., `rapp_swarm/build.sh`,
  `rapp_swarm/provision-twin.sh`). `installer/` is the *external*
  install surface only.
- ❌ **Documentation about installation.** Install discussion that
  isn't an installable file → `docs/` or a vault note. The scripts
  in this directory should self-document via their `--help` and
  header comments.

## Conventions

- **Stable filenames.** Install URLs are sacred (Article V). Once a
  file in `installer/` has a public URL, it does not get renamed,
  reshaped, or moved into a subdirectory. The `_<version>.zip`
  pattern is fine; the `install.sh`/`install.ps1`/`install.cmd`
  triple is fixed forever.
- **Versioned bundles append, not replace.** When a new Copilot
  Studio bundle ships, drop in `MSFTAIBASMultiAgentCopilot_1_0_0_6.zip`
  alongside the existing one. Old versions stay reachable for
  customers who haven't migrated. Update `installer/index.html` and
  the Tier 3 vault note to point at the new default.
- **Self-documenting headers.** Every shell/PowerShell script begins
  with a comment block showing the canonical curl/irm command.
  Update the comment if you ever change the URL.
- **No subdirectories.** Subdivision (`installer/scripts/`,
  `installer/templates/`, `installer/bundles/`) would change every
  public URL and break Article V. Stay flat.

## Scale rule

When you're about to add a file here:

1. *Is a user going to download or curl this directly?* Yes →
   `installer/`. No → tier directory.
2. *Will the URL `…/installer/<file>` need to be stable forever
   from the moment it lands?* Yes → name it carefully. No → it
   probably doesn't belong here at all.
3. *Is this a versioned artifact (zip, ARM template, bundle)?* If
   yes, name it with the version in the filename so future
   versions can coexist.

If a new install kind appears (a new platform, a new tier, a new
bundle format), add it as a sibling file. Don't restructure the
directory.

## Related

- Install one-liner sacredness:
  [`../CONSTITUTION.md`](../CONSTITUTION.md) Article V.
- Repo-root residency rule: Article XVI.
- Versioning + rollback contract: Article XIX,
  [`../docs/VERSIONS.md`](../docs/VERSIONS.md).
