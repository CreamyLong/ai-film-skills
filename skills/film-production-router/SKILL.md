---
name: film-production-router
description: Diagnose a problem in an AI film, short drama or novel-to-film production and assign it to the responsible production roles in order. Use when the user says the story, storyboard, assets, keyframes, prompts, voice, continuity, generated footage or final film has problems, or does not know which production stage should fix it. Returns a routing decision and task packages; does not itself write, generate, review media, approve assets or run other skills.
---

# Film Production Router

## Outcome

Identify the earliest responsible layer of a production problem, decide which roles must handle it and in what order, and produce a task package each role can execute without redesigning the whole film. A routing decision is not a repair and not an approval.

## Triage before assigning work

1. Restate the symptom as an observable fact: what is wrong, where it occurs, and what evidence shows it.
2. Identify the current stage and the earliest layer where the defect could have been introduced: source, screenplay, directing, storyboard, assets, animatic or previs, keyframes, prompt compilation, generation execution, sound, editing, ledger or state, or final delivery.
3. Separate verified facts, unknowns, assumptions and locked decisions. A missing fact is routed as an unknown to resolve, never as an invented fix.
4. Check whether the symptom is one defect or several. Different layers keep separate tasks; do not merge them into one vague "regenerate" instruction.

Worked symptom-to-role examples are in [routing-cases.md](references/routing-cases.md).

## Routing rules

- Assign each problem to the role that owns its cause, not the role that noticed it. A wrong face in a generated clip may belong to the keyframe or asset layer, not the video layer.
- Order tasks from the earliest responsible layer outward. Downstream work waits until its upstream input is fixed and rechecked.
- Every task package states: symptom and evidence, scope, locked facts to preserve, inputs to use, expected output, recheck criteria, and what must not change.
- A role returns evidence, not a verdict on layers it does not own. The router rechecks the routing decision after each handoff.
- Unknowns that change story meaning, cost, permissions or locked structure are returned to the user before downstream work continues.
- never route "regenerate" as a fix for a defect whose cause has not been located.

## Role map

Use the role codes below. The host maps each code to the skill registered for that role in the repository registry; the router does not name or invoke other skills.

| Code | Owns |
|---|---|
| DIRECTOR | story causality, character action, dialogue, director decisions before storyboarding |
| STORYBOARD | viewing order, blocking, cinematography, shot continuity |
| CHARACTER_ASSET | character identity, appearance, wardrobe and state references |
| SCENE_ASSET | location layout, entrances, landmarks, light sources and materials |
| PROP_ASSET | prop form, structure, material, handling and state |
| GENRE_VISUAL | genre-specific visual language applied to existing story, assets and shots |
| PRODUCTION_CONTROL | production contracts joining beats, asset registry, blocking, lighting and action |
| VIDEO_PRODUCTION | actual generation, selection, editing, sound, playback review and repair |
| MARKET_RESEARCH | market questions answered from verifiable official sources |
| KNOWLEDGE_REVIEW | review and versioned writing of approved knowledge |
| WEB_INTERFACE | website or application interface design and implementation |

## Output contract

Return, in order:

1. **Symptom and evidence** — what is wrong and how it was observed.
2. **Earliest responsible layer** — and why later layers cannot fix it alone.
3. **Routing table** — role code, task, inputs, expected output, recheck criteria, order.
4. **Blocked or unknown items** — what must be decided or verified before work proceeds.
5. **Not routed** — problems deliberately left out of scope and why.

## Boundaries

- This router does not write screenplays, design shots or assets, compile prompts, generate media, review images or audio, approve anything, or submit model calls.
- It does not guarantee that the host can switch skills automatically. If the host cannot continue into the assigned skill, return the task package so the user can invoke it directly.
- Routing by symptom is a hypothesis until the owning role checks the actual material. Do not present a routing decision as a diagnosis of media content.
- User-locked story structure, shot order, timing and dialogue are preserved unless the user authorizes a change.
