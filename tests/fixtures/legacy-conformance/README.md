# Legacy conformance-test quarantine

Files below this directory preserve the exact bytes of executable tests that
positively asserted retired pre-rev-5 identity, frame, egg, browser, Tier 2, or
wire behavior at commit `4c2b999`. Their final `.txt` suffix is intentional:
they are migration evidence, not executable tests and never RAPP/1 conformance
evidence.

The authoritative inventory is
[`../rapp1-retired-test-inventory.json`](../rapp1-retired-test-inventory.json).
Current negative and migration fixtures remain executable only where that
inventory records their exact disposition.
