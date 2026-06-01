# Apache OpenDAL Go Binding Services — Threat Model (v1 draft)

**Status:** v1 draft, authored by the ASF Security Team for OpenDAL PMC
review. Drafted against `apache/opendal-go-services` (default branch `main`),
2026-06-01.

**Provenance legend:** *(documented)* — from the repo's own docs/README/
layout; *(maintainer)* — ratified by an OpenDAL PMC member; *(inferred)* —
reasoned from structure / domain norms, **not yet confirmed** (each has a
matching §14 item).

**Draft confidence:** documented ~7 · maintainer 0 · inferred ~8.

**Relationship to the core model:** this repo is a thin distribution layer.
The data-access trust boundaries (caller→`Operator`, OpenDAL→backend,
credentials, paths, hostile-backend handling) are modelled once in
**`apache/opendal`'s `THREAT_MODEL.md`** (PR apache/opendal#7641); this
document only states what is *specific to this repo* and defers the rest.

**Revision triggers:** a new bundled service backend; a change to the FFI/ABI
the Go binding loads; a shift from "prebuilt-artifact distribution" to
shipping first-party logic.

---

## §1 Header

- **Project:** `apache/opendal-go-services` — "pre-build go binding services
  release": the repo that packages/distributes **pre-built service libraries**
  consumed by OpenDAL's Go binding. *(documented — README, `.asf.yaml`)*
- **Scope:** this repository only. The OpenDAL Rust core and its data-access
  model are out of scope here (covered by `apache/opendal`#7641). *(documented)*

## §2 Scope and intended use

The repo provides prebuilt, per-service artifacts the **Go binding** links
against, one directory per bundled backend: `s3`, `gcs`, `azblob`, `oss`,
`gdrive`, `aliyun_drive`, `fs`, `memory`, plus `internal`. *(documented — repo
layout)* The intended consumer is a **Go application** using OpenDAL via the
Go binding; this repo is the delivery vehicle for the service code that
binding loads. *(inferred — Q1)*

### Component families

| Family | Role / trust notes |
|---|---|
| Bundled service artifacts (`s3`, `gcs`, …) | Prebuilt backend implementations exposed across the cgo/FFI boundary to Go. The *logic* is OpenDAL-core logic compiled for the binding. *(inferred — Q2)* |
| `internal/` | Binding glue / loader plumbing. *(inferred — Q2)* |

## §3 Out of scope (explicit non-goals)

- **The data-access threat model itself** — credentials, per-backend auth,
  signed URLs, hostile-backend handling, path traversal: all modelled in
  `apache/opendal`#7641. A finding about *how a backend handles credentials or
  responses* belongs against the core, not here. *(inferred — Q3)*
- **Build/release/supply-chain hygiene** — artifact signing, reproducible
  builds, release provenance. Out of scope per the threat-model rubric (§1);
  these are governed by the ASF release process. *(documented — rubric)*
- The Go binding's *own* source (lives in `apache/opendal:bindings/`), beyond
  the ABI contract this repo's artifacts satisfy. *(inferred — Q3)*

## §4 Trust boundaries

1. **Go application → loaded service artifact (FFI/cgo).** The boundary this
   repo's artifacts sit on: a Go caller invokes backend operations that cross
   into the prebuilt (Rust-origin) code. *(inferred — Q4)*
2. **Service artifact → remote backend (network).** Same network boundary the
   core model describes; not re-derived here. *(documented — defer to #7641)*

## §5 Assumptions about the environment

Go runtime + cgo; the host platform the prebuilt artifact targets. *(inferred — Q5)*

## §6 Inputs — per-parameter trust

| Input | Source | Trusted? | Notes |
|---|---|---|---|
| Backend config + credentials | Go host app | Trusted (secret) | Same contract as core §6; this repo passes them through to the bundled backend. *(inferred — Q4)* |
| Object paths / data / ranges | Go caller | Untrusted-capable | Same handling/responsibility as core §6/§10. *(inferred — defer)* |
| Which prebuilt artifact is loaded | Go build/config | Trusted | Loading an unexpected/corrupted artifact is a supply-chain concern (out of scope §3). *(inferred — Q6)* |

## §7 Adversary model

Defers to the core (`apache/opendal`#7641 §7): data/path influencer + network
MITM + (likely) malicious backend in scope; in-process Go caller out of scope.
This repo adds no new adversary beyond the FFI-boundary integrity of the
loaded artifact. *(inferred — Q7)*

## §8 / §9 Properties provided / not provided

This repo provides **no security properties of its own** beyond faithfully
delivering the core's behaviour across the FFI boundary — the provided/not-
provided properties are the core model's (§8/§9 of #7641). It does **not**
add encryption, integrity, or isolation. *(inferred — Q8)*

## §10 Downstream responsibilities

Same as the core (credential mgmt, endpoint trust, path sanitization, size
bounding — see #7641 §10), plus: ensure the Go build links the **expected,
integrity-checked** artifacts (supply-chain, governed by ASF release
process). *(inferred — Q6)*

## §11a Known non-findings (seed — PMC to expand, Q18a)

- "This repo ships prebuilt binaries" — distribution of release artifacts is
  the ASF release process, not a code vulnerability in this repo. *(inferred)*
- "Credentials flow through the bundled backend" — same contract as the core;
  not a finding here. *(inferred — defer to #7641 §11a)*

## §13 Triage dispositions

| Disposition | When |
|---|---|
| **DEFER-TO-CORE** | The finding is about data-access logic / credentials / backend handling → route to `apache/opendal`#7641's model |
| **OUT-OF-MODEL** | Build/release/supply-chain, or the in-process Go caller |
| **VALID** | A defect specific to *this repo's* FFI-loader glue under the core §7 adversary |
| **MODEL-GAP** | Plausible, not covered → escalate to PMC |

## §14 Open questions for the maintainers

1. **(Q1)** Confirm this repo is purely a prebuilt-Go-binding-services release vehicle (no first-party data-access logic authored here).
2. **(Q2)** Are the per-service dirs (`s3`, `gcs`, …) prebuilt artifacts, or do any contain repo-original code that should be modelled here?
3. **(Q3)** Confirm the data-access model + the Go binding source are out of scope here (covered by core / bindings).
4. **(Q4)** Confirm the FFI/cgo boundary is the only repo-specific trust boundary; credentials/config just pass through to core logic.
5. **(Q5)** Any platform/runtime assumptions specific to the prebuilt artifacts worth stating?
6. **(Q6)** Is artifact integrity (right binary, not tampered) considered the ASF release process's job (out of scope here)?
7. **(Q7)** Confirm no adversary beyond the core model applies to this repo.
8. **(Q8)** Confirm this repo adds no security properties of its own.
9. **(Q18a)** What do scanners report against this repo that you consider non-findings?
10. **(meta)** OK to land this thin model as `THREAT_MODEL.md` here with the `AGENTS.md → SECURITY.md → THREAT_MODEL.md` chain, explicitly deferring to the core model?

## §15 Machine-readable companion

Not generated for v1.
