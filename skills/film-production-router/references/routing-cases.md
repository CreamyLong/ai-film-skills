# Routing cases

Worked examples of symptom-to-role assignment. Each case names the observable symptom, the earliest layer that can own it, and what must be rechecked before downstream work resumes. These are routing hypotheses, not media diagnoses.

## Story and directing

| Symptom | Earliest layer | Route | Recheck |
|---|---|---|---|
| Plot does not connect between scenes | Screenplay | DIRECTOR | Cause and effect chain, character knowledge and goals |
| Character acts against established motive | Screenplay | DIRECTOR | Behavior, alternatives rejected, consequence |
| Dialogue says one thing, scene needs another | Screenplay | DIRECTOR | Subtext, listener effect, character voice |
| Audience cannot tell who controls the scene | Directing | DIRECTOR, then STORYBOARD | Power geometry, viewing order |

## Assets

| Symptom | Earliest layer | Route | Recheck |
|---|---|---|---|
| Same character looks like a different person across shots | Character asset or keyframe | CHARACTER_ASSET, then VIDEO_PRODUCTION | Reference identity against actual keyframes |
| Room layout changes when the camera reverses | Scene asset | SCENE_ASSET, then STORYBOARD | Shared layout, entrances, landmarks, light direction |
| Prop changes hands or state without explanation | Prop asset or storyboard | PROP_ASSET or STORYBOARD | Prop lifecycle and shot-to-shot handoff |
| Character or prop appears with no prepared asset | Asset inventory | CHARACTER_ASSET, SCENE_ASSET or PROP_ASSET | Every visible subject has an approved reference |

## Keyframes and prompts

| Symptom | Earliest layer | Route | Recheck |
|---|---|---|---|
| Keyframe already shows the wrong subject or framing | Keyframe | VIDEO_PRODUCTION keyframe review, with asset roles as needed | Actual image against storyboard and assets |
| Prompt asks for a hand close-up but adds facial performance | Prompt compilation | VIDEO_PRODUCTION | Compiled text against visible subjects and body regions |
| Dialogue exists in the script but not in the submitted prompt | Prompt compilation | VIDEO_PRODUCTION | Source dialogue against the actual submission record |
| Reference images exceed model capacity | Submission | VIDEO_PRODUCTION | Declared attachments against the actual request |

## Generation and sound

| Symptom | Earliest layer | Route | Recheck |
|---|---|---|---|
| Voice changes between clips of the same character | Sound route | VIDEO_PRODUCTION | Voice reference actually attached, then actual audio |
| Background changes between angles of one room | Scene asset or generation | SCENE_ASSET, then VIDEO_PRODUCTION | Spatial ledger against actual frames |
| Previous clip tail does not match the next opening | Editing or generation | VIDEO_PRODUCTION | Actual tail and head frames, not redrawn stills |
| Generated clip is a still slideshow | Generation | VIDEO_PRODUCTION | Real motion in the actual clip |
| Old clip reused after prompt or reference changed | Ledger or state | VIDEO_PRODUCTION | Current request fingerprint against the stored one |

## Whole film

| Symptom | Earliest layer | Route | Recheck |
|---|---|---|---|
| Individual clips pass but the film does not read as one story | Screenplay or editing | DIRECTOR, then VIDEO_PRODUCTION | Full playback at normal speed |
| Novel adaptation loses the causal spine | Source breakdown | DIRECTOR | Source spans against screenplay decisions |
| Scenes are missing or assembled out of order | Ledger or editing | VIDEO_PRODUCTION | Scene order and completeness against the plan |
| Market or genre question blocks a creative decision | Research | MARKET_RESEARCH, then DIRECTOR | Dated official sources, stated limits |

## Not routing

- A request that already names its stage and artifact (for example "rewrite this dialogue") goes straight to the owning role; the router adds no value.
- A routing decision never replaces the owning role's own review of the actual material.
- If two layers could own a symptom, route to the earlier one first and state what evidence would move it downstream.
