# GLO-9 — [Brownfield] frontend is a 7-service gRPC coupling hub — introduce a backend-for-frontend seam to reduce change amplification

- **identifier:** GLO-9
- **url:** https://linear.app/global-south-ai-safety/issue/GLO-9/brownfield-frontend-is-a-7-service-grpc-coupling-hub-introduce-a
- **team:** Global South Ai Safety
- **status:** Backlog
- **labels:** Brownfield
- **priority:** High (2)
- **snapshot captured:** 2026-06-27T15:33:09+00:00

## Description

## Finding

`frontend` is the highest-degree coupling hub in Online Boutique: it opens **7 outbound gRPC client connections** (adservice, cartservice, checkoutservice, currencyservice, productcatalogservice, recommendationservice, shippingservice). `checkoutservice` is the second hub with **6** outbound edges. All edges use a single shared contract (`protos/demo.proto`), meaning a contract change to any downstream service can ripple into `frontend`'s wire-up, and a `demo.proto` change fans out to every service at once.

## Concrete files

* `src/frontend/main.go` — the `mustConnGRPC(...)` block wiring all 7 backends.
* `src/checkoutservice/main.go` — the 6-backend `mustConnGRPC(...)` block.
* `protos/demo.proto` — the single shared gRPC contract every service couples to.

## Why it matters

High efferent coupling at `frontend` (degree 7) concentrates change-amplification: any backward-incompatible contract change in one of the 7 downstream services forces a coordinated redeploy of `frontend`. The shared `demo.proto` means no service can evolve its API independently without touching the contract all consumers import. This elevates the blast radius of every API change and increases the recurring interest paid as friction on every future feature.

## Proposed refactor (first step)

Introduce an explicit **backend-for-frontend** (BFF) seam in `src/frontend/` that isolates UI-orchestration logic from the 7 raw service contracts. Split `protos/demo.proto` per bounded context (catalog, cart, checkout, shipping, ads, recommendations, currency) so a contract change no longer fans out to all services. The BFF layer translates between the UI's view model and each backend's domain contract.

## Grounded in

Grounded in: `sam-newman-building-microservices.md` (content coupling and the interplay of coupling and cohesion — a backward-incompatible contract forces upstream consumers to change in lockstep; incremental migration and nested bounded contexts for decomposition).
Grounded in: `balancing-coupling-in-software-design.md` (coupling strength measured as integration strength × distance × volatility — a high-CE hub amplifies change propagation across the system).
Grounded in: `managing-technical-debt.md` (the economic spotlight — coupling debt carries principal and recurring interest paid as friction on every future change; remediation cost/benefit analysis and the tipping point where interest exceeds value).
Grounded in: `architecture-for-flow.md` (bounded contexts as coarse-grained microservice candidates following high cohesion and loose coupling; microservices introduce operational complexity that must be justified by clear boundaries).
Grounded in: `strategic-monoliths-and-microservices.md` (microservices are about purpose and bounded context encapsulation, not size — the word "micro" is misleading; each business capability must have a complete implementation inside its context).
Grounded in: `software-architecture.md` (service granularity tradeoffs; independent deployability requires that services not share common coupling points like monolithic contracts; deployment boundaries must align with architecture quanta).
Grounded in: `accelerate.md` (loosely coupled architecture is the key architectural property enabling delivery throughput — tightly coupled systems are a significant barrier to increasing tempo and stability of the release process).
Grounded in: `lean-enterprise.md` (throughput and stability metrics — change lead time, deployment frequency, time to restore service, and change fail rate — all degrade when services cannot be tested and deployed independently).

## Acceptance criteria

- [ ] BFF/anti-corruption seam introduced in `src/frontend/` isolating the 7 gRPC clients from UI orchestration.
- [ ] `protos/demo.proto` split per bounded context — no single all-service contract.
- [ ] `src/checkoutservice/main.go` audited: its 6 outbound edges evaluated for a similar BFF or aggregator pattern.
- [ ] No service imports another service's stubs directly; each bounded context owns its contract.
