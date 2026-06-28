# GLO-15 — [Brownfield] frontend is a 7-service gRPC coupling hub — extract a backend-for-frontend boundary

- **identifier:** GLO-15
- **url:** https://linear.app/global-south-ai-safety/issue/GLO-15/brownfield-frontend-is-a-7-service-grpc-coupling-hub-extract-a-backend
- **team:** Global South Ai Safety
- **status:** Canceled
- **labels:** Brownfield
- **priority:** High (2)
- **snapshot captured:** 2026-06-28T21:26:36+00:00

## Description

## Finding

`frontend` is the highest-degree coupling hub in Online Boutique: it opens **7 outbound gRPC client connections** (adservice, cartservice, checkoutservice, currencyservice, productcatalogservice, recommendationservice, shippingservice). `checkoutservice` is the second hub with **6**. All edges flow through the single shared contract `protos/demo.proto`.

## Concrete files

* `src/frontend/main.go` — the `mustConnGRPC(...)` block wiring all 7 backends.
* `protos/demo.proto` — the single shared gRPC contract every service couples to.

## Why it matters

A change to any of the 7 backend contracts can ripple into `frontend`, and a `demo.proto` change touches every service at once. High efferent coupling (CE=7) at this hub concentrates change-amplification and blast radius: a backward-incompatible proto change forces all dependent consumers to change in lockstep. This is structural coupling debt that carries recurring interest paid as friction on every future feature that touches the orchestration surface.

## Proposed refactor (first step)

Introduce an explicit anti-corruption / backend-for-frontend (BFF) seam in `src/frontend/` so UI-orchestration concerns are isolated from the 7 service contracts. Split `protos/demo.proto` per bounded context so a contract change no longer fans out to all services.

## Grounded in

Grounded in: software-architecture.md (efferent coupling CE / afferent coupling CA — breaking apart a high-CE component reduces change amplification, and independent deployability fails when services share coupling points)
Grounded in: balancing-coupling-in-software-design.md (efferent coupling — the number of upstream components sharing knowledge with a given component; distance affects lifecycle coupling and cascading-change coordination cost)
Grounded in: sam-newman-building-microservices.md (the interplay of coupling and cohesion — a backward-incompatible contract forces upstream consumers to change in lockstep; nested bounded contexts and decomposition boundaries)
Grounded in: managing-technical-debt.md (technical debt as an economic issue — coupling debt carries recurring interest paid as friction on every future change, and the cost-benefit trade-off of remediation vs. carrying the debt)
Grounded in: architecture-for-flow.md (bounded contexts as coarse-grained microservice candidates — loose coupling and high cohesion are the key principles for identifying service boundaries)
Grounded in: strategic-monoliths-and-microservices.md (extracting bounded contexts from a monolith — look for quick wins based on rate of change, autonomy needs, and independent deployability)
Grounded in: accelerate.md (loosely coupled architecture as a top driver of delivery throughput and deployment performance — tight coupling overwhelms communication bandwidth with fine-grained implementation coordination)
Grounded in: lean-enterprise.md (IT performance measured by throughput and stability metrics — change lead time, deployment frequency, time to restore service, change fail rate — all degraded by tight architectural coupling)

## Acceptance criteria

- [ ] BFF/anti-corruption seam introduced in `src/frontend/` isolating the 7 gRPC clients behind a facade.
- [ ] `protos/demo.proto` split per bounded context (no single all-service contract).
- [ ] No service imports another service's protobuf stubs directly — all inter-service communication through well-defined service-specific contracts.
- [ ] `frontend`'s efferent coupling reduced from 7 to ≤ 3 well-defined BFF contracts.

## Review

After you open a PR for this ticket, run Greptile on it (/greptile) and address the findings before requesting merge.
