# Tiered capacity gating in stdlib Python

Most multi-tenant SaaS products gate operations by subscription tier — Free can have N items, Pro can have 10×N, Enterprise unlimited. The tier-enforcement logic typically lives in a billing system or a feature-flag service, both of which add SaaS dependencies.

For a stdlib Python service, you can do tier gating in about 80 lines without external dependencies. The pattern is straightforward enough to be worth writing down.

**The data model:**

```python
from dataclasses import dataclass

@dataclass
class TierLimits:
    name: str
    max_swarms: int
    max_peers: int
    max_memory_mb: int
    max_snapshots: int          # 0 = unlimited
    governance_amendments_allowed: bool
    sealing_allowed: bool
    monthly_price_usd: float

TIERS = {
    "free":     TierLimits("Free",     max_swarms=1,  max_peers=5,    max_memory_mb=100, max_snapshots=0,  governance_amendments_allowed=False, sealing_allowed=False, monthly_price_usd=0),
    "personal": TierLimits("Personal", max_swarms=10, max_peers=100,  max_memory_mb=10_000, max_snapshots=100, governance_amendments_allowed=False, sealing_allowed=True,  monthly_price_usd=29),
    "heritage": TierLimits("Heritage", max_swarms=50, max_peers=500,  max_memory_mb=100_000, max_snapshots=500, governance_amendments_allowed=True,  sealing_allowed=True,  monthly_price_usd=299),
    # ... etc
}
```

A `TierLimits` dataclass per tier. Capacity numbers + boolean feature flags. The tier definitions are *data*, not code — easy to reason about, easy to A/B test, easy to expose to a customer-facing comparison table.

**The store:**

```python
class TierStore:
    """Per-tenant tier subscription state, file-backed."""

    def __init__(self, root: Path):
        self.tiers_dir = root / "tiers"
        self.tiers_dir.mkdir(parents=True, exist_ok=True)

    def get_tier(self, tenant_id: str) -> str:
        p = self.tiers_dir / f"{tenant_id}.json"
        if not p.exists():
            return "free"
        return json.loads(p.read_text()).get("tier", "free")

    def set_tier(self, tenant_id: str, tier: str) -> None:
        if tier not in TIERS:
            raise ValueError(f"unknown tier: {tier}")
        (self.tiers_dir / f"{tenant_id}.json").write_text(
            json.dumps({"tier": tier}, indent=2)
        )
```

One JSON file per tenant. Tier name. Done. For production with many tenants you'd want this in Redis or Postgres; for development and modest scale, the filesystem is fine.

**The gate:**

```python
class TierLimitExceeded(Exception):
    def __init__(self, msg, tier, operation, current, limit, upgrade_to):
        super().__init__(msg)
        self.tier = tier; self.operation = operation
        self.current = current; self.limit = limit
        self.upgrade_to = upgrade_to

    def to_dict(self):
        return {
            "error": "tier_limit_exceeded",
            "message": str(self),
            "tier": self.tier,
            "operation": self.operation,
            "current_value": self.current,
            "limit": self.limit,
            "upgrade_to_unblock": self.upgrade_to,
        }


class TierGate:
    def __init__(self, root: Path):
        self.store = TierStore(root)

    def get_limits(self, tenant_id: str) -> TierLimits:
        return TIERS[self.store.get_tier(tenant_id)]

    def check_add_swarm(self, tenant_id: str, current_swarm_count: int):
        limits = self.get_limits(tenant_id)
        if current_swarm_count >= limits.max_swarms:
            upgrade = self._next_tier_with(
                self.store.get_tier(tenant_id),
                lambda t: t.max_swarms > current_swarm_count,
            )
            raise TierLimitExceeded(
                f"Tier {limits.name} allows {limits.max_swarms} swarms; you have {current_swarm_count}.",
                tier=limits.name, operation="add_swarm",
                current=current_swarm_count, limit=limits.max_swarms,
                upgrade_to=upgrade,
            )

    def check_seal(self, tenant_id: str):
        limits = self.get_limits(tenant_id)
        if not limits.sealing_allowed:
            raise TierLimitExceeded(
                f"Tier {limits.name} does not allow sealing.",
                tier=limits.name, operation="seal",
                current=False, limit=False, upgrade_to="personal",
            )

    def _next_tier_with(self, current: str, predicate) -> Optional[str]:
        order = ["free", "personal", "heritage", "founder", "institutional", "dynasty"]
        try:
            start = order.index(current) + 1
        except ValueError:
            start = 0
        for t in order[start:]:
            if predicate(TIERS[t]):
                return t
        return None
```

Each `check_*` method enforces one limit. They throw a structured exception that includes the upgrade target — so your error message can say *"upgrade to Heritage to unblock"* instead of a generic "limit exceeded."

**Use in HTTP handlers:**

```python
def do_POST_add_swarm(self, tenant_id):
    try:
        gate.check_add_swarm(tenant_id, current_swarm_count(tenant_id))
    except TierLimitExceeded as e:
        return self._send_json(402, e.to_dict())   # 402 Payment Required
    # ... actually add the swarm ...
```

Status code `402 Payment Required` is the right one for tier-gated rejection (better than `403 Forbidden` which implies an authorization issue, not a quota one). The error envelope tells the client what tier would unblock the operation.

**The full pattern fits in one file.** No SaaS dependency. Tests are dictionaries-in, exceptions-out, easy to verify without spinning up infrastructure. The tier definitions are publishable to your pricing page (the data is the same; the customer-facing pricing table is one render away).

**What this doesn't include:**

- **Billing.** Tier changes are recorded here; payment that triggered the change happens elsewhere (Stripe webhook hits an endpoint that calls `store.set_tier(tenant_id, new_tier)`). Decoupled deliberately — billing complexity stays in the billing module.
- **Per-resource quotas with reset windows.** "100 API calls per hour" is a different problem (rate limiting, not tier gating). Use a different module.
- **Soft limits / overages.** Some products allow exceeding the limit but charge extra. Add this if needed; the dataclass + exception structure can carry an `overage_allowed` field and `check_*` methods can report (without throwing) when exceeded.

**The lesson:**

Tier gating is one of those problems where the obvious solution (a SaaS dependency) is more complex than the bespoke version. ~80 lines of dataclasses + a JSON file per tenant covers the 90% case for any product with under 10 tiers and modest scale. You retain full control over limit logic, error messages, upgrade flows, and the data shape that hits your pricing page.

When you outgrow the file-per-tenant model (you will eventually if successful), the migration to Redis-backed or Postgres-backed storage is mechanical — replace `TierStore` internals; the `TierGate` interface doesn't change. The tier-definition data stays the same. The check methods stay the same. Only the persistence layer moves.

Start small. Stdlib. Files. Move on when you have to.
