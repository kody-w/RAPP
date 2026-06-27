# Hatching cubby-rapp-installer.egg

This egg is a `brainstem-egg/2.3-cubby` cartridge. Hatching it reconstitutes a
complete, **repo-independent** RAPP brainstem — the rapp-installer engine,
ported out of the grail.

## Three ways to hatch

**1. From the public RAPP Cave (one line, recommended — no auth):**
```bash
curl -fsSL https://kody-w.github.io/RAPP/cave/rapplications/rapp-installer/bootstrap.sh | bash
```

**2. From a local egg (sneakernet / already downloaded):**
```bash
# extract the hatcher out of the egg, then run it:
python3 - cubby-rapp-installer.egg <<'PY'
import sys, zipfile
open("hatch.py","wb").write(zipfile.ZipFile(sys.argv[1]).read("cubby/rapplications/rapp-installer/hatch.py"))
PY
python3 hatch.py cubby-rapp-installer.egg --run
```

**3. Natively, via a brainstem that already has the god agent / egg hatcher:**
```
cubby_import path=cubby-rapp-installer.egg      # native cubby op
# …or drop the egg in chat: "hatch /path/to/cubby-rapp-installer.egg"
```

## Where it lands

`~/.brainstem/cubbies/rapp-installer/` — a non-git cubby. Run it with
`python3 rapplications/rapp-installer/serve.py` (port 7077 by default).

## What it never does

Touch `~/.brainstem/src/rapp_brainstem` (the grail). `hatch.py` refuses to
hatch into it; `serve.py` refuses to boot against it.
