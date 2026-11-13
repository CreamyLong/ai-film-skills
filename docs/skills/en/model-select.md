# model-select — generation model selection and routing

| Status | New source package; structural checks only. The selection rules have not been validated on a real production task yet. |
|---|---|
| Can deliver alone | A reproducible selection: route, model identifiers, parameters, forbidden cases and fallback order. No media is produced. |
| Cannot claim alone | It does not supply models, accounts, credits or deployment, cannot guarantee a model exists in the target environment, and does not certify the finished film. |

[Runtime `SKILL.md`](../../../skills/model-select/SKILL.md) · [Install current source](../../INSTALLATION.md) · [Install](../../INSTALLATION.md) · [Compatibility](../../COMPATIBILITY.md) · [Design system](../../SKILL_DESIGN_SYSTEM.md)

No release snapshot yet; install from the current source tree.

<!-- contract:purpose -->
## 1. Purpose

Choose the generation model, parameters and fallback order for the deliverable at hand: stills and keyframes, single-shot video, multi-reference identity, segmented long takes, character voice and music.

<!-- contract:principles -->
## 2. Design principles

- Choose from the deliverable and its acceptance criteria, not from model reputation.
- Capability limits matter more than settings: name the cases where a route must not be used before tuning parameters.
- Consistency comes from a single source: one generation route per scene, one voice source per character.

<!-- contract:standalone -->
## 3. Standalone scope

Use this module by itself when the requested result stays inside the following boundary:

A reproducible selection: route, model identifiers, parameters, forbidden cases and fallback order. No media is produced.

**Cannot claim alone:** It does not supply models, accounts, credits or deployment, cannot guarantee a model exists in the target environment, and does not certify the finished film.

<!-- contract:inputs -->
## 4. Inputs

- The deliverable to produce, its target aspect ratio, duration and sample rate, and the acceptance criteria.
- The actually available model inventory and deployment state, plus authorization and cost limits for local or cloud execution.

<!-- contract:workflow -->
## 5. Workflow

1. Route by deliverable and state a primary route, a fallback route and the cases where neither should be used.
2. Check deployment state; treat unverified or undeployed capability as unavailable and run a single-variable smoke test before production.
3. Record a reproducible selection: model identifier, adapter, steps, cfg, canvas, frame count and seed.

<!-- contract:returns -->
## 6. Return, rework, and rollback

- When output fails, return to the selection layer first: wrong route, parameters outside the model contract, or insufficient reference material.
- Do not treat swapping models as a universal repair; locate the earliest wrong layer before changing the route.

<!-- contract:review -->
## 7. Review gates

- [ ] Change one variable per comparison and keep the control result.
- [ ] Before delivery confirm one source per scene and one voice source per character.
- [ ] A selection that names a model but cannot be reproduced from the recorded identifiers and parameters is incomplete.

<!-- contract:pass -->
## 8. Pass standard and states

- The deliverable meets its acceptance criteria and the recorded selection can be reproduced.
- A fallback route exists and unverified capability has not entered production.

> A pass below means this module's stated gates were met. Structural validity, real-task evidence, and user acceptance remain separate states.

<!-- contract:outputs -->
## 9. Outputs

- A selection: route, model identifiers, parameters, forbidden cases and fallback order.
- Optional single-variable smoke tests with their comparison result.

<!-- contract:boundaries -->
## 10. Boundaries, dependencies, and permissions

- It does not supply models, accounts, credits or deployment; the inventory is whatever the target environment actually provides.
- It does not replace directing, asset or dubbing decisions, and it does not certify the finished film.

<!-- contract:agents -->
## 11. Cross-Agent use

- The canonical package is the complete Skill folder, not a copied prompt fragment.
- `agents/openai.yaml` is optional Codex UI metadata and is not a runtime dependency for other hosts.
- Any host that can read files can produce a text selection. Running the chosen route additionally needs the model, media tooling and authorization that the target environment actually has.
- An Agent may read the instructions without native Skill discovery, but prompt-only reading must not be described as native integration.

<!-- contract:sources -->
## 12. Source files and references

**Runtime and metadata**

- [`SKILL.md`](../../../skills/model-select/SKILL.md)

**Distribution notices in new ZIP builds**

New builds attach these files inside the Skill folder without editing its runtime source. Historical release archives are unchanged.

- [`LICENSE`](../../../LICENSE)
