# sound-asset — voice and sound identity contract

| Status | New source package; structural checks only. No generated-sample listening review, real-task evidence or user acceptance yet. |
|---|---|
| Can deliver alone | A sound design, individually written audition or sample tasks, and a contract that later dubbing or generation can read; actual samples only when requested, possible and authorized. |
| Cannot claim alone | It does not dub the film, time lines to shots, mix, or prove voice consistency in the finished video; those require the actual production audio to be heard. |

[Runtime `SKILL.md`](../../../skills/sound-asset/SKILL.md) · [Install current source](../../INSTALLATION.md) · [Install](../../INSTALLATION.md) · [Compatibility](../../COMPATIBILITY.md) · [Design system](../../SKILL_DESIGN_SYSTEM.md)

No release snapshot yet; install from the current source tree.

<!-- contract:purpose -->
## 1. Purpose

Define reusable sound identities: a character's voice (casting, source, audible traits, sample set, performance baseline), an ambience bed, a signature effect, or a music theme, with rights and state.

<!-- contract:principles -->
## 2. Design principles

- Establish an auditable, versioned sound identity before dubbing, native audio-video generation, or mixing.
- A voice asset answers who is speaking; line-by-line performance answers how a line is spoken. Emotion is never a new voice.
- One speaker has one reviewed voice source per work, and every alias in the script maps to it. Changing the source is recasting.
- Reference use, cloning, upload, paid generation and commercial delivery are separate authorizations recorded with rights evidence.
- Only sounds reused across shots or scenes become assets; a one-off foley hit or a single scene's music edit stays in that scene's sound design.
- Reuse unchanged source context for local revisions. Asset identifiers remain internal; unreviewed samples block formal dubbing, not candidate text design.
- A voice is tracked by source, audible traits, aliases, rights and story-time state—not by a preset name alone.

<!-- contract:standalone -->
## 3. Standalone scope

Use this module by itself when the requested result stays inside the following boundary:

A sound design, individually written audition or sample tasks, and a contract that later dubbing or generation can read; actual samples only when requested, possible and authorized.

**Cannot claim alone:** It does not dub the film, time lines to shots, mix, or prove voice consistency in the finished video; those require the actual production audio to be heard.

<!-- contract:inputs -->
## 4. Inputs

- The script or description that establishes each speaker's age, origin, body state, relationships and timeline, plus the reading scope actually covered.
- The asset category (voice, ambience bed, signature effect, music theme), a unique ID, version, purpose and fields that remain unknown.
- The chosen or candidate voice route, available tools, any approved reference audio, and the rights and authorization state for each consequential action.

<!-- contract:workflow -->
## 5. Workflow

1. Choose design-text, actual-sample or scoped-diagnosis delivery and the asset category before using a template.
2. Derive audible traits from character or space facts; separate script facts, design assumptions and critical unknowns.
3. Check that speakers sharing scenes can be told apart by ear, and normalize every alias to one speaker.
4. Plan the reference sample set (neutral baseline, upper and lower intensity, long line) or the bed, effect or theme sample, and write each audition text individually.
5. Record the voice route, source identifier or reference hash, reproduction settings, rights and authorizations; create the machine-readable asset contract.
6. For text-only delivery, audible checks remain not_evaluated. Actual sample failures are rework; only explicit user listening can approve an asset.

<!-- contract:returns -->
## 6. Return, rework, and rollback

- Wrong age, gender impression or accent returns to the design basis; speakers that cannot be told apart return to casting.
- A character sounding like a different person across clips returns to the route and binding: was the source actually attached, or was a speaker silently skipped?
- Missing lines return to alias mapping and source identifiers; spoken stage directions return to separating instructions from dialogue.
- A failed review remains `rework`; structural completion cannot auto-promote it.

<!-- contract:review -->
## 7. Review gates

- [ ] ID, version, category, purpose, speaker aliases, locked features, voice source, rights and unknowns are explicit.
- [ ] Samples in one set sound like one person, repeat synthesis stays stable, and the audition text is spoken verbatim without stage directions.
- [ ] Voice samples are dry and single-speaker; beds loop without story events; effects are single clean events; themes are recognizable and do not imitate a named work or artist.
- [ ] File duration, sample rate, channels and hashes come from measurement; ASR read-back and speaker similarity are evidence, not approval, and are marked unverified when the tool is absent.
- [ ] Each speaking character has exactly one voice source; age and accent fit the character; scene partners are distinguishable; rights and each authorization are unambiguous.

<!-- contract:pass -->
## 8. Pass standard and states

- The sample task and JSON contract pass the module checklist with no unresolved blocking field or unauthorized action.
- `assets_approved` requires the user to listen to the actual samples, identified by path and hash; a text contract alone remains pending review.

> A pass below means this module's stated gates were met. Structural validity, real-task evidence, and user acceptance remain separate states.

<!-- contract:outputs -->
## 9. Outputs

- A voice design with audition texts and a performance baseline, or an ambience, signature-effect or music-theme sample task, at the requested scope.
- A versioned JSON sound-asset contract with source, rights, listening-review and state fields for dubbing, prompts, mixing and QC.

<!-- contract:boundaries -->
## 10. Boundaries, dependencies, and permissions

- Do not write or run scripts to batch-generate prompts through template loops, substitution, concatenation or model calls. Author and review each complete prompt individually; scripts may only validate or preserve completed text unchanged. Compilation, later polishing and batch requests grant no exception.
- Do not invent missing source facts, overwrite approved features, or put a specific shot's dialogue timing, lip sync or mix levels into the asset identity.
- Without an audio tool, authorization and listening review, this module delivers a sample task and contract, not finished or approved audio.
- Installing or running this module grants no voice rights, cloning permission, upload permission, paid credits or music rights.

<!-- contract:agents -->
## 11. Cross-Agent use

- The canonical package is the complete Skill folder, not a copied prompt fragment.
- `agents/openai.yaml` is optional Codex UI metadata and is not a runtime dependency for other hosts.
- Text contracts work in any host that can read the folder. Producing and approving actual samples additionally requires a speech, sound-effect or music tool, file access, the relevant rights and authorizations, and human listening review.
- An Agent may read the instructions without native Skill discovery, but prompt-only reading must not be described as native integration.

<!-- contract:sources -->
## 12. Source files and references

**Runtime and metadata**

- [`agents/openai.yaml`](../../../skills/sound-asset/agents/openai.yaml)
- [`SKILL.md`](../../../skills/sound-asset/SKILL.md)

**References**

- [`references/ambience-sfx-music-assets.md`](../../../skills/sound-asset/references/ambience-sfx-music-assets.md)
- [`references/NEGATIVE-CASE-BOOK.md`](../../../skills/sound-asset/references/NEGATIVE-CASE-BOOK.md)
- [`references/voice-casting-and-audition.md`](../../../skills/sound-asset/references/voice-casting-and-audition.md)

**Distribution notices in new ZIP builds**

New builds attach these files inside the Skill folder without editing its runtime source. Historical release archives are unchanged.

- [`LICENSE`](../../../LICENSE)
