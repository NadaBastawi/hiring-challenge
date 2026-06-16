# ABOUT.md

## Why this role

I want to work on AI that has real consequences if it gets it wrong. Contact discovery that routes to the wrong person, a voice agent that mishandles a dispute these aren't demo failures, they're relationship and legal failures. That's the kind of problem I find worth solving. The fact that the founder still reviews every PR and the hiring process is a real problem instead of leetcode tells me this is a team that thinks the same way.

## How I work with AI tools

I write the architecture first, then use Claude to implement against it. That way I'm reviewing code against a spec I own, not just accepting whatever it generates. I trust it for boilerplate and edge cases. I override it when it sounds confident but can't be verified which, in this challenge, is exactly the failure mode being tested.

## My last project — AgentForge TriageCrew

A multi-agent system that automates GitHub issue triaging using a 4-agent sequential pipeline (Issue Intake → Triage Analyst → Maintainer Response → Quality Gate), structured LLM reasoning, and a FastAPI benchmarking layer.

**One ambiguity I faced**: how much autonomy to give LLM agents vs. enforcing deterministic rules. GitHub issues vary wildly in structure and quality — fully relying on LLM reasoning made the system flexible but unpredictable; strict heuristics improved consistency but broke on edge cases. I resolved it by splitting responsibility: deterministic routing where classification confidence is high, LLM interpretation for nuanced or ambiguous inputs. The boundary between those two modes was the hardest design decision in the project.

**One tradeoff I made**: pipeline modularity vs. latency. The 4-agent sequential design made each step inspectable and failures localized, but it was measurably slower — end-to-end triage ran at 5–8 seconds per issue vs. ~2 seconds for a single-agent approach. I chose modularity because it mirrors real production workflows and makes evaluation and iteration significantly easier, but I'd revisit parallelizing the intake and triage steps if latency became a hard constraint.

**One mistake I made**: over-relying on LLM outputs without validation. The triage agent misclassified infrastructure and setup issues as feature requests roughly 25–30% of the time because the prompt didn't anchor on existing GitHub labels or structured metadata. I caught it only when benchmarking revealed the inconsistency. The fix was adding a confidence scoring mechanism, a quality gate agent to validate before returning output, and explicitly feeding GitHub labels as structured signals into the prompt. The lesson: LLMs fill gaps with plausible answers — if your prompt doesn't give them the right anchors, they'll invent reasonable-looking ones.

**One review comment that changed my mind**: "Is this actually better than a simpler single-agent solution?" That question reframed the whole project. I had been focused on showcasing the multi-agent architecture; the feedback pushed me to justify it with measurable impact. I added explicit evaluation metrics, built the FastAPI benchmarking layer, and restructured how I documented design decisions — from "here's what I built" to "here's why this design outperforms the alternative." It shifted my mindset from building something complex to justifying complexity with evidence.

## What I'd improve about this challenge

The two-stage gate is genuinely well-designed — committing `PLAN.md` before reading clarifications forces honest planning rather than retrofitting assumptions. One thing I'd add: a single sentence in `PROBLEM.md` stating whether the output feeds directly into automated outreach or is reviewed by a human first. That fork changes the confidence threshold design significantly and the precision-vs-recall tradeoff entirely — I had to surface it as a clarifying question rather than knowing upfront.
