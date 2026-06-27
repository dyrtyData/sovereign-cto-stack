# GLO-10 — [Brownfield] frontend is a 7-service gRPC coupling hub — extract a backend-for-frontend boundary

- **identifier:** GLO-10
- **url:** https://linear.app/global-south-ai-safety/issue/GLO-10/brownfield-frontend-is-a-7-service-grpc-coupling-hub-extract-a-backend
- **team:** Global South Ai Safety
- **status:** Backlog
- **labels:** Brownfield
- **priority:** High (2)
- **snapshot captured:** 2026-06-27T23:35:19+00:00

## Description

## Finding

`frontend` is the highest-degree coupling hub in Online Boutique: it opens **7 outbound gRPC client connections** (adservice, cartservice, checkoutservice, currencyservice, productcatalogservice, recommendationservice, shippingservice). `checkoutservice` is the second hub with **6** (cartservice, currencyservice, emailservice, paymentservice, productcatalogservice, shippingservice). All edges flow through the single shared contract `protos/demo.proto`.

## Concrete files

* `src/frontend/main.go` — the `mustConnGRPC(...)` block wiring all 7 backend clients.
* `src/checkoutservice/main.go` — the 6-backend `mustConnGRPC(...)` block.
* `protos/demo.proto` — the single shared gRPC contract every service couples to.

## Why it matters

A backward-incompatible protobuf change to any one of the 7 backend contracts ripples into `frontend`. A `demo.proto` change fans out to all 12 services simultaneously. High efferent coupling (outbound degree 7) at the frontend hub concentrates change-amplification, blast radius, and blocks independent releasability — teams working on backend services cannot release without coordinating with the frontend team.

## Proposed refactor (first step)

Introduce an explicit backend-for-frontend (BFF) / anti-corruption seam in `src/frontend/` so UI-orchestration concerns are isolated from the raw gRPC service contracts. Split `protos/demo.proto` per bounded context (e.g. `proto/checkout.proto`, `proto/catalog.proto`, `proto/shipping.proto`) so a contract change no longer fans out to all services. No service should import another service's stubs directly.

## Grounded in

Grounded in: sam-newman-building-microservices.md (information hiding and loose coupling — client code must not bind too tightly to service interfaces; backward-incompatible changes force consumers to change in lockstep)
Grounded in: managing-technical-debt.md (coupling debt carries recurring interest paid as friction on every future change; remediation cost weighed against the savings from reduced interest)
Grounded in: architecture-for-flow.md (bounded contexts encapsulating domain models are good coarse-grained candidates for microservices; loosely coupled, self-contained services enable flow)
Grounded in: strategic-monoliths-and-microservices.md (bounded context encapsulation drives right-sized service boundaries — size is contextual, not a target)
Grounded in: software-architecture.md (not every portion of an application must be microservices — over-decomposition is one of the biggest pitfalls)
Grounded in: accelerate.md (loosely coupled architecture is the key property enabling teams to test and deploy independently — tight coupling blocks delivery throughput)
Grounded in: lean-enterprise.md (delivery throughput and stability metrics — lead time, deployment frequency, change fail rate — are blocked when services cannot be tested and deployed independently)
Grounded in: agentic-architectural-patterns-for-building-multi-agent-systems.md (the path from simpler architecture to microservices must be driven by concrete scaling demand, not premature decomposition)

## Acceptance criteria

- [ ] BFF/anti-corruption seam introduced in `src/frontend/` isolating the 7 raw gRPC clients behind UI-domain interfaces.
- [ ] `protos/demo.proto` split per bounded context (no single all-service contract).
- [ ] No service imports another service's generated stubs directly.
- [ ] `src/frontend/main.go` outbound degree reduced from 7 to fewer than 4 direct dependencies.
