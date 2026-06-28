# GLO-16 — [Brownfield] checkoutservice — billing-path gRPC coupling hub (degree 6) + SonarQube issue: fuse DETECT+KEEP, route to Codegen

- **identifier:** GLO-16
- **url:** https://linear.app/global-south-ai-safety/issue/GLO-16/brownfield-checkoutservice-billing-path-grpc-coupling-hub-degree-6
- **team:** Global South Ai Safety
- **status:** Backlog
- **labels:** Brownfield
- **priority:** High (2)
- **snapshot captured:** 2026-06-28T20:03:50+00:00

## Description

## Finding

`checkoutservice` is a **billing-path coupling hub** in Online Boutique: it opens **6 outbound gRPC client connections** (cartservice, currencyservice, emailservice, paymentservice, productcatalogservice, shippingservice) — the second-highest coupling degree after `frontend` (7). It is ALSO flagged by SonarQube. This ticket FUSES two complementary static signals: graphify (KEEP) for cross-service coupling, and SonarQube (DETECT) for code quality.

**SonarQube scan (DETECT):** 240 issues project-wide — 230 code smells, 7 bugs, 3 vulnerabilities (ncloc 5856, complexity 550). `checkoutservice` carries SonarQube issues directly on `src/checkoutservice/main.go`.

**graphify coupling (KEEP):** `checkoutservice` outbound gRPC degree = 6; `frontend` = 7. All edges share the single monolithic contract `protos/demo.proto`.

## Concrete files

* `src/checkoutservice/main.go` — the 6-backend `mustConnGRPC(...)` block (graphify coupling evidence_file) AND the file the cited SonarQube issue sits in.
* `src/frontend/main.go` — the 7-backend `mustConnGRPC(...)` block (the highest-degree hub).
* `protos/demo.proto` — the single shared gRPC contract every service couples to.

## SonarQube issue

SonarQube issue: 0e054858-e16b-4d96-983f-f2c08e5fb68e (go:S1135 / INFO / CODE_SMELL) at online-boutique:src/checkoutservice/main.go:L151 — Complete the task associated to this TODO comment.

(selected from the fused `static_analysis.exemplar_issue` in `graphify-out/service-coupling.json`, on the billing-path coupling hub.)

## Why it matters

A change to any of the 6 backend contracts ripples into `checkoutservice`, and a `demo.proto` change touches every service at once — maximum change-amplification. Because this is the **billing path** (cart / checkout / payment / currency), a defect or coupling change here directly threatens revenue, which is why it is the **priority surface** for remediation (the P2 billing-path audit folded into this P3 slice). High efferent coupling carries structural interest: every future feature pays friction across 6 integration points.

## Proposed refactor (first step)

Proposed refactor — route to **Codegen** (the agentic multi-file SWE remediation back-end registered under `mcp_servers` in `hermes/config.yaml`): introduce an explicit anti-corruption seam in `src/checkoutservice/` isolating the 6 service contracts behind a single orchestration boundary, and resolve the flagged SonarQube issue in the same change. This is a novel, judgment-heavy refactor spanning gRPC wiring + contract boundaries, so Codegen fits better than a mechanical recipe. Moderne/OpenRewrite (the deterministic recipe engine) is the recipe-amenable alternative for mechanical debt; evaluating it (paid, no free tier) is rolled into <issue id="26b9b2b4-03bc-4762-8a65-b32e16553218" href="https://linear.app/global-south-ai-safety/issue/GLO-14/brownfield-frontend-is-a-7-service-grpc-coupling-hub-extract-a-backend">GLO-14</issue>. Then split `protos/demo.proto` per bounded context so a contract change no longer fans out to all services.

## Grounded in

Grounded in: balancing-coupling-in-software-design.md (efferent coupling — the number of upstream components a component depends on; distance amplifies lifecycle coupling and cascading-change coordination cost)
Grounded in: sam-newman-building-microservices.md (coupling types ranked low-to-high; a backward-incompatible contract forces all upstream consumers to change in lockstep)
Grounded in: software-architecture.md (CE/CA coupling analysis — breaking apart a high-efferent-coupling component reduces change amplification; not every portion of an application has to be microservices)
Grounded in: managing-technical-debt.md (coupling debt carries recurring interest paid as friction on every future change; remediation cost must be weighed against accumulating interest before the tipping point)
Grounded in: architecture-for-flow.md (bounded contexts with high cohesion and loose coupling are the right coarse-grained candidates for microservices; microservices introduce operational complexity that must be earned)
Grounded in: strategic-monoliths-and-microservices.md (microservices are about purpose, not size; a bounded context encapsulates a complete business capability — no leftover fragments outside it)
Grounded in: accelerate.md (a loosely coupled architecture is the top driver of delivery throughput — enabling teams to independently test and deploy without fine-grained cross-team coordination)
Grounded in: lean-enterprise.md (IT performance measured by change lead time, deployment frequency, time-to-restore, and change fail rate — all degraded by tight coupling)

## Acceptance criteria

- [ ] Anti-corruption seam introduced in `src/checkoutservice/` isolating the 6 clients behind a single orchestration boundary
- [ ] The cited SonarQube issue (0e054858-e16b-4d96-983f-f2c08e5fb68e) on `src/checkoutservice/main.go` is resolved in the same change
- [ ] `protos/demo.proto` split per bounded context (no single all-service contract definition)
- [ ] Remediation routed to Codegen (named back-end); each resulting deployment unit testable/releasable independently

## Review

After you open a PR for this ticket, run Greptile on it (/greptile) and address the findings before requesting merge.
