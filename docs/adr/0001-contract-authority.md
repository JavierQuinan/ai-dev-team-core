# ADR 0001 — Contract authority and extraction

Status: Proposed. Source: Marketplace PR #36 semantic contracts at 86983b158ee09a2ce04fcd96dfaa86573ae1317e; acceptance and runtime evidence pending. This ADR does not declare those contracts released.

## Decision
Core owns provider-neutral wire specifications after explicit acceptance. Marketplace owns native workflow semantics; natural-language equivalent handoffs remain valid. Adapters translate at the boundary. Cloud owns runtime enforcement, scheduling and commercial behavior. SDK owns provider translation. No dependency from Core to any consumer.

Use JSON Schema 2020-12; version envelopes independently of package versions. Closed objects for initial security-sensitive contract candidates; additive changes require compatibility review (closed readers can reject new fields). Major incompatible changes require migration. Never claim semantic validation from schema checks alone.

## Mapping
| Marketplace artifact | Core candidate | Additional constraints |
|---|---|---|
| Design handoff | DesignHandoff | unresolved material decisions block freeze |
| Implementation contract | TaskPacket + ImplementationContract | dependency order and ownership |
| Agent output | AgentResult | executed checks, non-actions and assumptions |
| Review findings | Finding | evidence, disposition and verification |
| Completion handoff | CompletionReport | actual stages, gates, deferrals, deviations |
| Coordination | TaskGraph + Approval | DAG, canonical paths, disjoint active writers |

## Gates
Validate the mapping against accepted #36 and #30; use positive and negative fixtures, exact-head evidence and independent review. Runtime evidence is not replaced by wire validation. A candidate schema may be developed before #36 acceptance, but no stable release or downstream production adoption. Preserve upstream notices and keep private implementation out of this repository.
