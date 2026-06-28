# GLO-19 — [Brownfield] frontend is a 7-service gRPC coupling hub (CE=7) — introduce a BFF anti-corruption seam and split contracts per bounded context

- **identifier:** GLO-19
- **url:** https://linear.app/global-south-ai-safety/issue/GLO-19/brownfield-frontend-is-a-7-service-grpc-coupling-hub-ce7-introduce-a
- **team:** Global South Ai Safety
- **status:** Backlog
- **labels:** Brownfield
- **priority:** High (2)
- **snapshot captured:** 2026-06-28T21:12:18+00:00

## Description

## Finding

`frontend` is the highest-degree coupling hub in Online Boutique: it opens **7 outbound gRPC client connections** (adservice, cartservice, checkoutservice, currencyservice, productcatalogservice, recommendationservice, shippingservice). `checkoutservice` is the second hub with **6** (cartservice, currencyservice, emailservice, paymentservice, productcatalogservice, shippingservice). All edges are direct gRPC calls — no anti-corruption layer, no BFF seam, no bounded-context contract isolation.

## Concrete files

* `src/frontend/main.go` — the `mustConnGRPC(...)` block wiring all 7 backends (evidence: all 7 `frontend→*` edges cite this file).
* `src/checkoutservice/main.go` — the 6-backend `mustConnGRPC(...)` block (evidence: all 6 `checkoutservice→*` edges cite this file).
* `src/recommendationservice/recommendation_server.py` — outbound edge to `productcatalogservice`.

## Why it matters

A contract change in any of the 7 backends can ripple into `frontend`, and any orchestration change in `frontend` can trigger churn across all 7 integrations. With 7 efferent edges (CE=7), `frontend` concentrates change-amplification and blast radius — a single backward-incompatible proto change in one downstream service forces the frontend team to absorb the hit. The absence of a BFF/anti-corruption seam means UI concerns are entangled with service-contract concerns.

## Proposed refactor (first step)

Introduce a Backend-for-Frontend (BFF) seam in `src/frontend/` that isolates the 7 gRPC clients behind an explicit orchestration boundary. Split contracts per bounded context (cart+checkout, catalog+recommendation, currency+shipping, ad) so a single downstream contract change no longer fans out to every consumer. The BFF becomes the single integration surface; each backend team owns its contract and can evolve independently.

## Grounded in

Grounded in: balancing-coupling-in-software-design.md (afferent coupling defined as the number of downstream components depending on a component; the balanced-coupling model frames strength × distance × volatility — high-CE frontend is strength-high distance-low, an unbalanced state that increases cognitive load to evolve).
Grounded in: software-architecture.md (efferent coupling CE and afferent coupling CA — breaking apart a high-CE component can reduce coupling when downstream consumers only need a subset of functionality; also the service granularity chapter cautions against making every piece a microservice).
Grounded in: managing-technical-debt.md (technical debt is ultimately an economic issue — coupling debt carries recurring interest paid as friction on every future change; the remediation ROI framework compares cost of refactor with reduced interest from lower ongoing friction).
Grounded in: architecture-for-flow.md (microservices candidates should follow high cohesion and loose coupling via bounded contexts; DORA/Accelerate metrics — deployment frequency, lead time, MTTR, change failure rate — are directly impacted by how coupled the architecture is).
Grounded in: strategic-monoliths-and-microservices.md (bounded contexts encapsulate a business capability and size is measured by the ubiquitous language, not line count; microservices are not about being "micro" — the tradeoff balances scalability/availability against performance/reliability/complexity).
Grounded in: accelerate.md (loosely-coupled architecture is the key architectural property enabling high delivery performance — teams can test and deploy individual components independently; tight coupling is a significant barrier to increasing both tempo and stability).

## Acceptance criteria

- [ ] BFF/anti-corruption seam introduced in `src/frontend/` isolating the 7 outbound gRPC clients behind a single orchestration boundary.
- [ ] gRPC contracts split per bounded context (no single all-service contract shared by all consumers).
- [ ] No service directly imports another service's generated stubs across bounded-context boundaries.
- [ ] `src/frontend/main.go` outbound degree reduced from 7 to ≤3 (the BFF plus necessary cross-cutting concerns).
