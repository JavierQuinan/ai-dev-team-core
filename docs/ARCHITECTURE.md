# Core architecture

Core owns canonical wire contracts, not commercial execution. Dependency direction: Marketplace, SDK and Cloud consume versioned Core artifacts; Core imports none of them. Start with JSON Schema 2020-12 and generated TypeScript types. Use SemVer, immutable releases, compatibility tests and explicit migration notes.

## Contract inventory
AgentDescriptor (role, capabilities, tool permissions); TaskPacket (id, runId, dependencies, objective, scoped read/write paths, criteria, budget, deadline); TaskGraph (acyclic nodes, edges); Handoff (producer, consumer, artifact refs, schema version, freeze state); AgentResult (status, evidence, findings, usage); Evidence (digest, provenance, command, exit status, redacted artifact ref); Approval (scope, actor, expiration, decision); ProviderCapabilities (supported features, isolation and approvals); RunEvent (sequence, timestamp, correlation).

Use stable IDs, explicit UTC timestamps, integer minor currency units or token counts, no plaintext secrets. Validation rejects unknown incompatible major versions, cycles, overlapping write ownership without serialization, invalid evidence references, expired approvals and missing mandatory gates. Policy declarations are not enforcement; adapters must enforce them at execution boundaries.

## Acceptance
Golden fixtures and negative cases, deterministic schema checks, compatibility across minor versions, generated types reproducible, no provider dependency or proprietary material. Align with Marketplace PR #36 before extracting contracts; do not create parallel incompatible definitions.
