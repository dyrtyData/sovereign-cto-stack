# AGENTS.md (Hermes profile layer) — Sovereign CTO Stack

This file is read by Hermes per working directory (the **project** layer, distinct from
`hermes/SOUL.md`, which is durable identity). It encodes the standing operating rules every
Hermes profile follows in this stack. The repo-root `../AGENTS.md` holds the broader
architecture; this file is the agent-facing operating contract, tightened in Phase 2 around
the CTO RAG brain.

## Rule #1 — Ground every CTO function in the corpus (Phase 2 onward)

**Before running ANY CTO function, you MUST call `query_cto_knowledge` first**, and you MUST
**cite the grounding text(s)** it returns (the `source_file` field) in your output. This is
not optional and applies to *every* CTO function, not just strategy briefs:

| CTO function | Consult `query_cto_knowledge` for | Typical grounding texts (cite the actual `source_file`) |
|---|---|---|
| Tech-debt / architecture audit (Phase 3) | service coupling, modularity, refactor strategy | *Building Microservices*, *Software Architecture: The Hard Parts*, *Balancing Coupling*, *Managing Technical Debt*, *Accelerate* |
| PMF / market research (Phase 4) | product-market fit, experimentation, growth | *The Lean Product Playbook*, *Hacking Growth*, *Lean Enterprise*, *Trustworthy Online Controlled Experiments* |
| Org / strategy / pivot decisions | org design, eng leadership, team topologies | *An Elegant Puzzle*, *The Engineering Executive's Primer*, *The Manager's Path*, *Team Topologies*, *Architecture for Flow* |

How to call it (the tool is bound via MCP as `mcp_cto_knowledge_query_cto_knowledge`):

```text
query_cto_knowledge(query="<the specific question>", k=5)
-> { "results": [ { "source_file": "...md", "heading": "...", "score": .., "text": "..." }, ... ] }
```

Workflow for any CTO task:
1. Formulate the precise question(s) the decision turns on.
2. Call `query_cto_knowledge` for each; read the returned passages.
3. Produce the deliverable, **citing the `source_file`(s)** that grounded each claim, e.g.
   _"Grounded in: building-microservices.md (on afferent/efferent coupling)."_
4. If the corpus returns nothing relevant, say so explicitly rather than inventing grounding.

## Rule #2 — Git history is the authoritative decision record

mem0 is a complement, not a dependency. Record decisions in commits and in
`docs/system-design-tradeoffs.md`. If mem0 is unavailable or wrong, the git log + tradeoffs
doc must still let a human reconstruct every decision.

## Rule #3 — Never commit secrets

Credentials live only in `.env` (repo, gitignored) and `~/.hermes/.env`. Config files
committed to the repo carry zero secret values (gitleaks-enforced).

## Rule #4 — Static analysis only for the audit target

Online Boutique (`microservices-demo`) is analyzed as a source graph (graphify) — never
deployed. K8s-only upstream; we only read the source.

## Rule #5 — Small, verifiable steps

Each phase boots and is verified before the next begins. Cite the corpus; commit the rationale.
