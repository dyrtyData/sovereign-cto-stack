# GLO-12 — [Product] Tech-debt auditor stops at diagnosis — add autonomous remediation that opens code-change PRs from filed [Brownfield] tickets

- **identifier:** GLO-12
- **url:** https://linear.app/global-south-ai-safety/issue/GLO-12/product-tech-debt-auditor-stops-at-diagnosis-add-autonomous
- **team:** Global South Ai Safety
- **status:** Backlog
- **labels:** Product
- **priority:** High (2)
- **snapshot captured:** 2026-06-27T15:33:12+00:00

## Description

## Current offering

The sovereignCTO stack today has a CTO-Architecture profile (`hermes/skills/file_brownfield_ticket.md`) that reads a graphify service-coupling graph, consults the CTO RAG brain via multi-angle `query_cto_knowledge` calls, and files HumanLayer-ready `[Brownfield]` Linear tickets that name exact source files and cite corpus-grounded refactor rationale. It does NOT generate remediation code changes — it stops at diagnosis and ticket filing. The CTO-Market profile (`hermes/skills/pmf_brief.md`) researches PMF questions and files `[Product]` opportunity tickets. Neither profile produces actual code-level fixes or opens pull requests.

## Market signal

Codegen ([https://codegen.com/ai-tools-for-technical-debt/](<https://codegen.com/ai-tools-for-technical-debt/>)) already has an autonomous remediation agent that "picks up debt tickets, implements fixes, and opens PRs without a developer in the loop." KPMG's 2025 M&A survey ([https://kpmg.com/kpmg-us/content/dam/kpmg/pdf/2026/how-ai-can-help-reduce-tech-debt-in-ma.pdf](<https://kpmg.com/kpmg-us/content/dam/kpmg/pdf/2026/how-ai-can-help-reduce-tech-debt-in-ma.pdf>)) found 52% of organizations had already piloted automated code refactoring. DevoxSoftware ([https://devoxsoftware.com/blog/overcoming-tech-debt-with-ai-a-practical-guide-for-smes/](<https://devoxsoftware.com/blog/overcoming-tech-debt-with-ai-a-practical-guide-for-smes/>)) reports that AI-driven contextualized remediation has reclaimed "up to 42% of developer time within two quarters" in SMEs. The market is moving from detection to autonomous remediation — our stack today only covers the detection-half of the loop.

## The gap (concrete capability)

Today the product detects coupling hotspots and files `[Brownfield]` tickets naming exact files and refactor rationale. The market wants the full detect → triage → **remediate** loop. The missing capability is: **autonomous code remediation that accepts a filed** `[Brownfield]` **ticket's concrete file findings and generates a proposed code-change PR (e.g., extracting a BFF seam, splitting a shared proto contract, upgrading a deprecated API call) with the same corpus-grounded rationale embedded in the PR description.**

## Proposed opportunity (first step)

Add a `remediate` step to the CTO-Architecture loop: after filing a `[Brownfield]` ticket, (optionally) spawn a remediation sub-agent that reads the ticket's concrete file paths, applies the proposed refactor to the actual source files, and opens a PR against the target repo. Scope to one well-defined refactor class first — extracting a backend-for-frontend (BFF) seam from a high-efferent-coupling frontend service — using the existing `src/frontend/main.go` as the canonical Online Boutique target. The remediation PR description must carry the same `Grounded in:` citation union as the parent ticket.

## Grounded in

Grounded in: the-lean-product-playbook.md (Product-Market Fit Pyramid — the remediation feature set is the next layer above diagnosis in the pyramid; customers are underserved in the solution space even though detection needs are met by incumbents)
Grounded in: lean-enterprise.md (validated learning — the BFF extraction is a scoped MVP experiment; do things that don't scale before automating the full remediation pipeline)
Grounded in: hacking-growth.md (North Star metric — engineering hours reclaimed, not tickets filed; the remediation loop is what converts diagnosis into actual time savings that drive acquisition and retention)
Grounded in: architecture-for-flow.md (competitive landscape — Codegen already offers autonomous PRs; delay in adding remediation cedes the full-loop position to incumbents)

## Acceptance criteria

- [ ] A `remediate` sub-agent reads a filed `[Brownfield]` ticket's concrete file paths and proposed refactor.
- [ ] For the BFF extraction class: the agent modifies `src/frontend/main.go` to introduce an anti-corruption seam isolating the 7 gRPC clients.
- [ ] A PR is opened (GitHub or Linear-connected) with a description carrying the same `Grounded in:` citations as the parent ticket.
- [ ] The PR is scoped to a single refactor class and produces a diff a human can review in under 30 minutes.
- [ ] Acceptance verified by running the full loop against Online Boutique: graphify → query_cto_knowledge → file [Brownfield] → remediate → PR opened.
