# film-production-router — problem triage and role routing

| Status | New routing entry; installation history and user acceptance are separate. |
|---|---|
| Can deliver alone | A routing decision with symptom, evidence, responsible layer, ordered tasks and recheck criteria. |
| Cannot claim alone | It does not write, generate, review media, approve anything, or invoke other skills; the host or user continues into the assigned skill. |

[Runtime `SKILL.md`](../../../skills/film-production-router/SKILL.md) · [Install current source](../../INSTALLATION.md) · [Install](../../INSTALLATION.md) · [Compatibility](../../COMPATIBILITY.md) · [Design system](../../SKILL_DESIGN_SYSTEM.md)

No release snapshot yet; install from the current source tree.

<!-- contract:purpose -->
## 1. Purpose

Diagnose a production problem, find its earliest responsible layer, and assign ordered task packages to the roles that own the fix.

<!-- contract:principles -->
## 2. Design principles

- Find the earliest layer that could have introduced the defect before assigning work; the role that noticed a problem does not own its fix.
- A routing decision is a hypothesis with evidence and recheck criteria, never a repair, an approval, or a media diagnosis.

<!-- contract:standalone -->
## 3. Standalone scope

Use this module by itself when the requested result stays inside the following boundary:

A routing decision with symptom, evidence, responsible layer, ordered tasks and recheck criteria.

**Cannot claim alone:** It does not write, generate, review media, approve anything, or invoke other skills; the host or user continues into the assigned skill.

<!-- contract:inputs -->
## 4. Inputs

- An observable symptom, the current production stage, available material and evidence, locked decisions, and any unknowns.

<!-- contract:workflow -->
## 5. Workflow

1. Restate the symptom, locate the earliest responsible layer, split multi-layer defects, and order tasks from that layer outward.
2. Each task package states scope, locked facts, inputs, expected output, recheck criteria and what must not change.
3. Restate the symptom as an observable fact, locate the earliest layer that could have introduced it, and split multi-layer defects into separate tasks.
4. Order tasks from the earliest responsible layer outward; downstream work waits for fixed and rechecked upstream inputs.

<!-- contract:returns -->
## 6. Return, rework, and rollback

- A routing table with role codes, ordered tasks, blocked or unknown items, and deliberately unrouted problems.

<!-- contract:review -->
## 7. Review gates

- [ ] The owning role checks the actual material; the router rechecks the routing decision after each handoff.
- [ ] A routing decision is a hypothesis until the owning role checks the actual material; unknowns that change story, cost or permissions return to the user.

<!-- contract:pass -->
## 8. Pass standard and states

- Every routed problem has an owner, an order, inputs, an expected output and observable recheck criteria.

> A pass below means this module's stated gates were met. Structural validity, real-task evidence, and user acceptance remain separate states.

<!-- contract:outputs -->
## 9. Outputs

- A routing decision and task packages the host or user can continue into the assigned skills.

<!-- contract:boundaries -->
## 10. Boundaries, dependencies, and permissions

- It does not write, design, generate, review media, approve anything, submit model calls, or guarantee automatic skill switching.

<!-- contract:agents -->
## 11. Cross-Agent use

- The canonical package is the complete Skill folder, not a copied prompt fragment.
- `agents/openai.yaml` is optional Codex UI metadata and is not a runtime dependency for other hosts.
- The host or user continues into the assigned skill; without that continuation the router returns task packages only.
- An Agent may read the instructions without native Skill discovery, but prompt-only reading must not be described as native integration.

<!-- contract:sources -->
## 12. Source files and references

**Runtime and metadata**

- [`SKILL.md`](../../../skills/film-production-router/SKILL.md)

**References**

- [`references/routing-cases.md`](../../../skills/film-production-router/references/routing-cases.md)

**Distribution notices in new ZIP builds**

New builds attach these files inside the Skill folder without editing its runtime source. Historical release archives are unchanged.

- [`LICENSE`](../../../LICENSE)
