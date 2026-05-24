# Theme and Metaphor Research (Parking Document)

**Status:** Parked — to be picked up after the v5 flow-restructure work lands.
**Owner decision required:** depth, family, scope.
**Do not reference the prior rename shortlist** (armature, furrow, jig, sow) as a starting point — the prior research was shallow and not engaging. Restart fresh when this thread resumes.

## Purpose

ADE has the opportunity to ship a cohesive metaphor across the SDLC pipeline — a sustained role-play / narrative system that names agents, phases, and status copy as parts of one world. This document captures what we've learned about the *opportunity space*, the *risks*, and the *open questions*, without locking in any specific naming or metaphor family.

The fresh research that resumes this thread should be substantially deeper than what's been done before. The previous rename research was shallow; this work needs to be grounded in real precedent, tested against the ADE aesthetic, and committed to with a clear-eyed view of what metaphor branding can and can't do.

## What we learned (current thread)

### The market space is mostly empty for cohesive SDLC narrative

- **Personas-as-functional-labels** is table stakes. CrewAI's `role`/`goal`/`backstory`, AutoGen Magentic-One's `WebSurfer`/`FileSurfer`/`Coder`, LangGraph supervisors, OpenAI Swarm named handoffs, Mastra instructions-as-personality — all common, none constitute a *world*.
- **Two real precedents** ship a sustained metaphor across the framework: [MetaGPT](https://github.com/FoundationAgents/MetaGPT) and [ChatDev](https://github.com/OpenBMB/ChatDev), both with a "virtual software company" frame (CEO → CTO → Programmer → Reviewer → Tester).
- **ChatDev 2.0 ("DevAll") deliberately backed away** from the company metaphor toward task-agnostic orchestration. That retreat is informative: heavy metaphor didn't compound into a moat, and the wrong metaphor is worse than none.
- **Single-agent dev tools** (Devin, OpenHands, Cursor, Cline, Aider, SWE-agent, Replit Agent) rely on a name, not a world. Devin is the most invested in anthropomorphism but it's one character, not a cast.
- **GitHub's mascot universe** (Mona the Octocat, Copilot mascot) lives in marketing, not in the agent UX.

**Verdict on the original claim:** Mostly correct. The corporate-frame ground is taken by MetaGPT/ChatDev. The workshop / lab / field-expedition / craft / agrarian metaphor space for agentic SDLC tools is genuinely unclaimed.

### Two directions are separable: metaphor vs. game mechanics

| Direction | Risk | Recommendation |
|---|---|---|
| **Cohesive role metaphor** — agent names, phase names, status copy use a sustained world | Low if one-layer-deep; locks you into a metaphor that's hard to change later | Worth pursuing |
| **Game mechanics** — XP, badges, achievements, streaks, level-up screens | High in pro dev tools; gamification literature is consistent that thin badge layers feel manipulative; Clippy is the canonical warning | Don't pursue |

Stack Overflow badges are the rare gamification success and only because they align with real economic value (proof of expertise). Even there, badges have been observed to degrade contribution quality.

### Three depth tiers for the metaphor itself

| Tier | What it looks like | Where it's safe |
|---|---|---|
| **Tier 1 — Themed naming** | Agents have evocative role names + one-line role descriptions. No narrative voice in output. | Default — ship this if pursuing the direction |
| **Tier 2 — Narrative voice** | Agents speak in role-flavored output; status updates use narrative tone | Optional layer; gate behind a flag |
| **Tier 3 — Full gamification** | XP, achievements, scoreboards | Don't ship in pro dev tooling |

## Design principles for whatever metaphor lands

These survive any specific metaphor choice and should constrain the fresh research:

1. **One layer deep, everywhere.** Agent names, phase names, CLI subcommands, status copy. No ASCII art, no mascots, no score screens. The metaphor is *consistent* across the surface, never *louder* than the work.

2. **Make the metaphor removable.** Ship a `--plain` flag (or `ADE_PLAIN=1`) that strips role names back to functional labels. This is cheap if designed in from the start; expensive to bolt on later. It protects against the Clippy failure mode and lets enterprise users opt out without forking.

3. **The metaphor must be decoration, not load-bearing.** Test: does removing the persona still leave a correct, useful sentence? If yes, the metaphor is doing its job. If no, the metaphor is doing work the architecture should be doing instead.

4. **Avoid corporate role names** (CEO/CTO/PM/VP). That ground is taken by MetaGPT and ChatDev, it's tired, and ChatDev's retreat suggests it doesn't compound. Workshop, lab, field, craft, naturalist, expedition vocabulary is open.

5. **Treat the metaphor as a brand wedge, not a moat.** ChatDev's retreat is the warning. The product still has to be good at orchestration; the metaphor only helps adoption and memorability. Don't over-invest as if the metaphor itself is the product.

## Risks specific to this direction

- **Heavy metaphor dates quickly.** "Cyber Detective" felt fresh in 2018; would look cringe in 2026. The chosen frame needs to be timeless rather than fashionable. Workshop and naturalist vocabulary ages well; cyberpunk and RPG vocabulary does not.
- **Cutesy branding undermines credibility for risky tools.** Devs hesitate to run something called "wizard" on production code. Restraint matters.
- **Narrative scaffolding adds tokens** to every prompt. Worth measuring before committing.
- **Persona naming locks you into a metaphor that's hard to change later.** Once docs, status logs, and skill prompts all reference a specific cast, renaming is non-trivial. Pilot before committing.

## Open questions for the fresh research

When this thread resumes, the fresh research should answer (in order):

1. **Metaphor family selection.** Workshop, naturalist's survey, field expedition, craft atelier, R&D lab, detective bureau, theater/film production — each has a different feel. Which fits ADE's actual emotional positioning? *Craft and care*, not bureaucracy and chain of command. This needs grounded exploration with concrete vocabulary examples, not a list.

2. **Persona cast.** Once the family is chosen, what are the role names? How many roles does the cast need? Should every agent have a persona, or only the user-facing ones? What about the orchestrator itself — does it have a name?

3. **Phase naming.** Do the phases themselves get themed names (e.g., "The Survey," "The Brief," "The Build"), or only the agents within them? Themed phase names are higher-commitment and higher-payoff.

4. **Voice & tone.** What does the status output sound like? Terse log entries with persona names, or full narrative ("Scouts report back from the eastern ridge")? Where on the verbosity spectrum is right for a dev tool?

5. **Pilot scope.** First-deployment scope: only the new Research-phase agents, or the full pipeline cast? The Research-phase agents are the cheapest pilot (they don't exist yet) and give the team a feel for whether the voice lands.

6. **Rename of the toolkit itself.** ADE (Agentic Development Environment) is functional but flat. Does the toolkit get a name that fits the chosen metaphor? This decision can run alongside or after the cast naming — it doesn't have to be first.

## What NOT to bring forward

- **The prior rename shortlist** (armature, furrow, jig, sow). Treat as discarded. Fresh exploration when this thread resumes.
- **Any specific persona names that came up in passing** during the v5 flow restructure conversation. Those were illustrative scaffolding, not committed proposals.
- **The corporate org-chart metaphor** (CEO/CTO/PM). Already taken, already retreating.

## Inputs to the fresh research (when it resumes)

- This document
- The grounded findings in the v5 flow-restructure thread (the architecture the cast will populate)
- Whatever ADE rename decision has or hasn't been made by then
- The user's aesthetic compass — grounded, evocative, professional, never cutesy
- Real precedents to study in depth: ChatDev's retreat (what didn't work), MetaGPT's persistence (what did), Linear's minimalism (the alternative to having a metaphor at all), Devin's single-character anthropomorphism (the one-character alternative)

## Sources from the current thread (for continuity)

- [MetaGPT](https://github.com/FoundationAgents/MetaGPT) — corporate-frame multi-agent SDLC
- [ChatDev](https://github.com/OpenBMB/ChatDev) — 7-role corporate metaphor; v2 "DevAll" retreat
- [Magentic-One](https://microsoft.github.io/autogen/stable//user-guide/agentchat-user-guide/magentic-one.html) — `-Surfer` naming hints at metaphor
- [CrewAI personas guide](https://docs.crewai.com/en/guides/agents/crafting-effective-agents)
- [Devin product analysis](https://ppaolo.substack.com/p/in-depth-product-analysis-devin-cognition-labs) — single-character anthropomorphism
- [Linear's brand](https://linear.app/brand) — the "no metaphor" alternative
- [Clippy's tragic life](https://www.mentalfloss.com/article/504767/tragic-life-clippy-worlds-most-hated-virtual-assistant) — the canonical warning
- [Growth Engineering — dark side of gamification](https://www.growthengineering.co.uk/dark-side-of-gamification/)
- Stack Overflow badge effects studies — gamification's rare success and its quality-degradation observations
