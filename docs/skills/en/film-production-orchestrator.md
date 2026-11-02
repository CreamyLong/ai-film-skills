# film-production-orchestrator — unified film creation and production

| Status | Renamed unified entry with creation and triage contracts; host orchestration and real-film acceptance remain separately unverified. |
|---|---|
| Can deliver alone | Task-specific briefs, prerequisite/asset checks, workflow and resumable handoff plans, or symptom-based triage, using bundled references without sibling dependencies. |
| Cannot claim alone | It cannot promise automatic host delegation, replace specialist craft, supply missing tools or approve media/spend. Plans are not finished films; unavailable capabilities and unperformed reviews stay explicit. |

[Runtime `SKILL.md`](../../../skills/film-production-orchestrator/SKILL.md) · [Install current source](../../INSTALLATION.md) · [Install](../../INSTALLATION.md) · [Compatibility](../../COMPATIBILITY.md) · [Design system](../../SKILL_DESIGN_SYSTEM.md)

No release snapshot yet; install from the current source tree.

<!-- contract:purpose -->
## 1. Purpose

Let users state a goal instead of choosing Skills; coordinate scoped creation, prerequisites, specialist handoffs, checks and repairs through the requested endpoint, while preserving problem triage.

<!-- contract:principles -->
## 2. Design principles

- One user entry owns goal interpretation, scope, prerequisites, handoffs and progress; specialist roles own creative and production craft. Select creation orchestration, problem triage or a direct stage without forcing a full pipeline.
- Continue through actual host-supported execution when authorized and available; a plan is not execution, a routing hypothesis is not a repair, and returned files are not approval.

<!-- contract:standalone -->
## 3. Standalone scope

Use this module by itself when the requested result stays inside the following boundary:

Task-specific briefs, prerequisite/asset checks, workflow and resumable handoff plans, or symptom-based triage, using bundled references without sibling dependencies.

**Cannot claim alone:** It cannot promise automatic host delegation, replace specialist craft, supply missing tools or approve media/spend. Plans are not finished films; unavailable capabilities and unperformed reviews stay explicit.

<!-- contract:inputs -->
## 4. Inputs

- A goal, story, reference video, song, product input, stage request or defect; the requested endpoint, available material/capabilities, valid approvals, locks, budget, rights and project progress.

<!-- contract:workflow -->
## 5. Workflow

1. Choose short-drama, reference-led TVC/promotion, music-led MV, product-film or repair guidance; recover the current project and stop at the requested endpoint. Identify needed people/views, spaces, props/products, voices and state variants without adding irrelevant assets.
2. Resolve roles from actually available host capabilities, dispatch ready tasks within permission, inspect returned artifacts and evidence, route failures to their earliest owner and resume affected downstream work. Missing delegation returns explicit blocked task packages, not simulated execution.
3. Creation mode selects a task-specific workflow and proactively discovers asset and tool prerequisites; triage mode restates evidence and locates the earliest defect layer. Direct stage requests skip unnecessary planning.
4. Keep task dependencies and review states in the existing project record, resume only verified inputs, and stop for bounded spend, missing authority, unknown submission outcomes or uninspectable deliverables.

<!-- contract:returns -->
## 6. Return, rework, and rollback

- The requested artifact plus actual validation state and residual issues; if blocked, completed work, unfinished scope, exact missing capability/approval and next action. Diagnosis-only requests receive the ordered triage table.

<!-- contract:review -->
## 7. Review gates

- [ ] Check real inputs, versions, required reviews, spend and returned evidence after every handoff. Media claims need actual viewing/listening; input changes stale affected tasks, and unknown submissions are reconciled before retry.
- [ ] A routing decision is a hypothesis until the owning role checks the actual material; unknowns that change story, cost or permissions return to the user.

<!-- contract:pass -->
## 8. Pass standard and states

- Each required task has an owner, pinned inputs/dependencies, output, status and observable acceptance criteria; only the requested endpoint with real evidence counts as complete. Plan, test, execution, full playback and user acceptance remain separate.

> A pass below means this module's stated gates were met. Structural validity, real-task evidence, and user acceptance remain separate states.

<!-- contract:outputs -->
## 9. Outputs

- Scoped creative/production deliverables through available specialists, resumable progress and task packages; or evidence-based triage and rechecks for defects.

<!-- contract:boundaries -->
## 10. Boundaries, dependencies, and permissions

- Do not write or run scripts to batch-generate prompts through template loops, substitution, concatenation or model calls. Pass individual authorship/review to specialist tasks; orchestration, compilation and batch-media requests grant no exception.
- It bundles no models, accounts, runtime scheduler or specialist packages and grants no review authority. Text-only work, maintenance or adopting an idea never authorizes media/spend; tool or evidence gaps cannot be hidden as successful output.

<!-- contract:agents -->
## 11. Cross-Agent use

- The canonical package is the complete Skill folder, not a copied prompt fragment.
- `agents/openai.yaml` is optional Codex UI metadata and is not a runtime dependency for other hosts.
- Standalone scope/planning/triage use only bundled references. Downstream execution requires actually available specialist roles and tools through the host; unavailable delegation is explicitly blocked rather than claimed.
- An Agent may read the instructions without native Skill discovery, but prompt-only reading must not be described as native integration.

<!-- contract:sources -->
## 12. Source files and references

**Runtime and metadata**

- [`SKILL.md`](../../../skills/film-production-orchestrator/SKILL.md)

**References**

- [`references/creation-workflows.md`](../../../skills/film-production-orchestrator/references/creation-workflows.md)
- [`references/orchestration-loop.md`](../../../skills/film-production-orchestrator/references/orchestration-loop.md)
- [`references/routing-cases.md`](../../../skills/film-production-orchestrator/references/routing-cases.md)

**Distribution notices in new ZIP builds**

New builds attach these files inside the Skill folder without editing its runtime source. Historical release archives are unchanged.

- [`LICENSE`](../../../LICENSE)
