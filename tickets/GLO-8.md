# GLO-8 — [Brownfield] frontend is a 7-service gRPC coupling hub — extract a backend-for-frontend boundary

- **identifier:** GLO-8
- **url:** https://linear.app/global-south-ai-safety/issue/GLO-8/brownfield-frontend-is-a-7-service-grpc-coupling-hub-extract-a-backend
- **team:** Global South Ai Safety
- **status:** Canceled
- **labels:** Brownfield
- **priority:** High (2)
- **snapshot captured:** 2026-06-28T21:26:34+00:00

## Description

## Finding

`frontend` is the highest-degree coupling hub in Online Boutique: it opens **7 outbound gRPC client connections** (productcatalogservice, currencyservice, cartservice, recommendationservice, shippingservice, checkoutservice, adservice). `checkoutservice` is the second hub with **6** (shippingservice, productcatalogservice, cartservice, currencyservice, emailservice, paymentservice). Every edge flows through the single shared contract `protos/demo.proto`. Source of the signal: the deterministic service-level coupling map `graphify-out/service-coupling.json`.

## Concrete files

* `src/frontend/main.go` — the `mustConnGRPC(...)` block wiring all 7 backend clients (`*_SERVICE_ADDR`).
* `src/checkoutservice/main.go` — the 6-backend `mustConnGRPC(...)` block.
* `protos/demo.proto` — the single shared gRPC contract every service couples to.

## Why it matters

`frontend` carries an efferent-coupling degree of 7 — the highest in the system. A backward-incompatible change to any of the 7 backend contracts ripples into `frontend`, and a `demo.proto` change touches every service at once: high change-amplification and a large blast radius. Beyond the structural risk, this is **carried technical debt** — the coupling levies ongoing *interest*, paid as friction on every future change to a backend or to the shared proto, and a redeploy is forced across the fan-out on each contract break. Loosely-coupling this hub is also a direct lever on delivery throughput.

## Proposed refactor (first step)

Introduce an explicit anti-corruption / backend-for-frontend (BFF) seam in `frontend` so UI-orchestration concerns are isolated from raw downstream service contracts. Split `protos/demo.proto` per bounded context (catalog, currency, cart, checkout, …) so a contract change to one domain no longer fans out to all services. Start by extracting the productcatalog and currency client paths behind a domain facade in `src/frontend/`.

## Grounded in

(Surfaced by `query_cto_knowledge` BEFORE this ticket was written, design Q5 — the auditor issued multiple angle queries (coupling, technical-debt economics, service decomposition/granularity, delivery throughput) and cites the UNION of the distinct corpus `source_file`s those queries returned. Retrieval decided these; nothing was pre-curated.)
Grounded in: software-architecture.md (efferent coupling CE vs afferent coupling CA, and "Service Granularity" — breaking apart a high-CE component reduces change amplification).
Grounded in: managing-technical-debt.md ("Shining an Economic Spotlight on Technical Debt" — coupling debt carries interest paid as friction on every change; T4 remediation cost/benefit).
Grounded in: sam-newman-building-microservices.md (the interplay of coupling and cohesion — a backward-incompatible contract forces upstream consumers to change in lockstep).
Grounded in: balancing-coupling-in-software-design.md (coupling strength and the distance over which a change propagates — the glossary of coupling).
Grounded in: strategic-monoliths-and-microservices.md (right-sizing service granularity and decomposition boundaries — "Are Microservices Good?").
Grounded in: architecture-for-flow.md (organizing service boundaries for flow / fast delivery, via Wardley-mapped platform boundaries).
Grounded in: accelerate.md (loosely-coupled architecture as a top driver of delivery throughput and deployment performance).
Grounded in: lean-enterprise.md (evolving platform boundaries to sustain delivery performance).

## Acceptance criteria

- [ ] BFF/anti-corruption seam introduced in `src/frontend/` isolating direct gRPC client calls behind domain facades.
- [ ] `protos/demo.proto` split per bounded context (no single all-service contract).
- [ ] No service imports another service's stubs directly.
- [ ] `frontend` efferent-coupling degree measured at <= 4 after refactor.
- [ ] Regression: all 7 downstream integrations still functional.
