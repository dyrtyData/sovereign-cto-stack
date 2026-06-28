# GLO-11 — [Brownfield] frontend is a 7-service gRPC coupling hub — extract a BFF boundary and split demo.proto

- **identifier:** GLO-11
- **url:** https://linear.app/global-south-ai-safety/issue/GLO-11/brownfield-frontend-is-a-7-service-grpc-coupling-hub-extract-a-bff
- **team:** Global South Ai Safety
- **status:** Backlog
- **labels:** Brownfield
- **priority:** High (2)
- **snapshot captured:** 2026-06-27T23:35:19+00:00

## Description

## Finding

`frontend` is the highest-degree coupling hub in Online Boutique: it opens **7 outbound gRPC client connections** (adservice, cartservice, checkoutservice, currencyservice, productcatalogservice, recommendationservice, shippingservice). `checkoutservice` is the second hub with **6** (cartservice, currencyservice, emailservice, paymentservice, productcatalogservice, shippingservice). All edges flow through the single shared contract `protos/demo.proto` — a contract change fans out to every service at once.

## Concrete files

* `src/frontend/main.go` — the `mustConnGRPC(...)` block wiring all 7 backends
* `src/checkoutservice/main.go` — the 6-backend `mustConnGRPC(...)` block
* `protos/demo.proto` — the single shared gRPC contract every service couples to

## Why it matters

A change to any of the 7 backend contracts can ripple into `frontend`, and a `demo.proto` change touches every service at once. The two highest-degree hubs concentrate change-amplification and blast radius; the single shared contract defeats independent deployability. This coupling carries recurring interest — every feature change that touches a contract incurs friction across every downstream consumer.

## Proposed refactor (first step)

Introduce an explicit **Backend-for-Frontend (BFF)** seam in `src/frontend/` so UI-orchestration concerns are isolated from the 7 service contracts. Split `protos/demo.proto` per bounded context (e.g. `catalog.proto`, `cart.proto`, `checkout.proto`, `currency.proto`) so a schema change no longer fans out to all services. This is the first-step Strangler Fig extraction: BFF first, then contract decomposition.

## Grounded in

Grounded in: architecture-for-flow.md (bounded contexts need inter-context APIs; coupling drives change amplification — "high cohesion and loose coupling" as the guiding principle for extracting microservice candidates — and software delivery performance as measured by DORA/Accelerate metrics depends on loosely coupled architecture)
Grounded in: sam-newman-building-microservices.md (microservice communication styles — synchronous gRPC coupling forces lockstep version upgrades; backward-incompatible contracts force all upstream consumers to change simultaneously)
Grounded in: managing-technical-debt.md (technical debt is an economic issue — coupling debt carries principal and recurring interest; the remediation cost/benefit tradeoff must weigh reduced interest against opportunity cost of delaying features; the tipping point is when interest cost exceeds the benefit of incurring the debt)
Grounded in: software-architecture.md (Chapter 7 Service Granularity — "not every portion of an application has to be microservices" — granularity decisions should be driven by coupling and cohesion, not a dogmatic "micro means small")
Grounded in: strategic-monoliths-and-microservices.md ("Not Too Big, Not Too Small" — microservices are about purpose, not size; a Bounded Context encapsulates a business capability completely, and cross-cutting coupling indicates the boundary is wrong)
Grounded in: accelerate.md (CHAPTER 5 ARCHITECTURE — "high performance is possible with all kinds of systems, provided that systems — and the teams that build and maintain them — are loosely coupled"; many SOA/microservice implementations fail to permit testing and deploying services independently)
Grounded in: lean-enterprise.md (delivery throughput is measured by change lead time, deployment frequency, time to restore service, and change fail rate — tight coupling degrades all four)

## Acceptance criteria

- [ ] BFF/anti-corruption seam introduced in `src/frontend/` isolating the 7 gRPC clients behind a single orchestration layer
- [ ] `protos/demo.proto` split per bounded context — no single all-service contract
- [ ] No service imports another service's stubs directly
- [ ] `frontend` outbound gRPC degree drops from 7 to ≤ 2 (BFF + auth gateway)
