---
title: "Research, Plan, Implement, Review: My Agentic Engineering Workflow"
date: 2026-02-22
description: |
  The most reliable way I've found to build with AI coding models is to separate work into distinct stages — research, planning, and implementation — with review cycles between each. You build up written artifacts that serve as a shared source of truth, implement in small phases, and review at every step.
options:
  categories:
    - AI
    - software-engineering
    - claude-code
    - workflow
---

The most reliable way I've found to build with AI coding models is to separate work into distinct stages — research, planning, and implementation — with review cycles between each. You build up written artifacts (`RESEARCH.md`, `PLAN.md`, `PLAN-CHECKLIST.md`) that serve as a shared source of truth, implement in small phases, and review at every step.

# The problem

Without structure, working with AI coding agents tends to go the same way: you give the model a prompt, it produces something that's close but not quite right, and you spend the rest of the session correcting it. As complexity grows, this back-and-forth compounds — the model carries forward bad assumptions, the context window fills up with failed attempts, and you end up doing most of the work yourself.

This process avoids that by:
- Building up written artifacts that persist across sessions and give the model a clear reference point
- Separating research, planning, and implementation so each gets focused attention
- Using review cycles to catch and correct mistakes before they compound
- Starting fresh sessions at each stage so the model isn't weighed down by prior confusion
- Working in small phases so problems stay contained and recoverable

# Principles

- **AI agents are fallible and cut corners.** They miss things, take shortcuts, and make confident-sounding mistakes. A single pass is rarely enough. Build in review cycles and expect to catch errors.
- **Fresh context windows prevent compounding confusion.** Starting a new session for each stage means the model isn't carrying forward misunderstandings or stale assumptions.
- **Written artifacts are the source of truth.** `RESEARCH.md`, `PLAN.md`, and `PLAN-CHECKLIST.md` are the shared ground truth between you and the model. Without them, context is lost between sessions and the model has to re-infer your intent every time.
- **Separate research, planning, and implementation.** Mixing them leads to the model jumping to code before it understands the problem. Keeping them in distinct phases forces rigor.
- **Small phases reduce blast radius.** A bug introduced in Phase 1 doesn't silently propagate through Phases 2–5 before anyone notices.
- **Your time is expensive, tokens are cheap.** Having the model research, plan, review, and revise across multiple sessions uses more tokens than a single prompt — but produces dramatically better results. Optimize for output quality, not token efficiency.
- **Let AI review before you do.** Before you spend time reviewing, let the model review first and address its own issues. By the time you look at it, the obvious problems are fixed and you can focus on what only a human would catch.
- **Git history is your safety net.** Committing after each phase means you can always revert. If a phase goes badly, roll back and try again.
- **Watch for over-engineering.** Left to their own devices, models tend to add unnecessary complexity:
  - Abstractions and helper functions you didn't ask for
  - Error handling for scenarios that can't happen
  - Configuration where hardcoded values would do
  - Features or refactoring beyond what was requested

  Be explicit about scope upfront. During review, ask the agent to identify where it may have over-engineered.

# The process

The steps below correspond to this diagram:

```{mermaid}
flowchart TD
    A[1. Problem Statement] --> B[2. Research]
    B --> C[3. Research Review]
    C --> C1{Satisfied?}
    C1 -- No --> B
    C1 -- Yes --> D[4. Planning]
    D --> E[5. Plan Review]
    E --> E1{Satisfied?}
    E1 -- No --> D
    E1 -- Yes --> F[6. Implement Phase N]
    F --> G[7. Implementation Review]
    G --> G1{Satisfied?}
    G1 -- No --> F
    G1 -- Yes --> H[8. Commit]
    H --> I{More phases?}
    I -- Yes --> F
    I -- No --> J[9. Final Review]
    J --> K{Issues resolved?}
    K -- No --> J
    K -- Yes --> L{Refactor?}
    L -- Yes --> M[10. Refactoring]
    M --> N[Done]
    L -- No --> N
```

1. **Start with a clear problem statement.** Describe the problem or feature. Provide supporting context — paths to relevant files or folders, reference documents, anything that helps the model understand the "what, why, or how": The problem it's meant to be solving, pointers to relevant areas of the codebase (or examples it can learn from), or initial guidance about how it should be thinking about solving the problem (this might even be presented in the form of multiple options to consider).

2. **Research.** Ask the agent to research the codebase (existing project) or do web research (greenfield), writing everything to `RESEARCH.md`. Read it yourself and revise as necessary — the model may miss things or get details wrong.

3. **Research review.** New session. Tell the agent: "Review RESEARCH.md for accuracy and completeness." Read its feedback, then tell it to revise. Answer any questions and tell it which points to ignore if any are off-base. Repeat until you're satisfied — getting the research right prevents bad assumptions from cascading into the plan.

4. **Planning.** New session. Give the agent your problem statement, tell it to read `RESEARCH.md` and develop a plan, saving to `PLAN.md`. For complex work, also have it write `PLAN-CHECKLIST.md` breaking work into phases and tasks — this gives the model a way to track progress during implementation.

5. **Plan review.** New session. Tell the agent: "Review PLAN.md as a senior engineer." Read its recommendations and clarifying questions, then tell it to revise. Tell it which points to ignore if any are off-base — e.g., "Revise PLAN.md to address your feedback, but ignore points 2 and 5." Repeat until the plan is solid.

6. **Implementation.** New session. "Implement Phase 1 of PLAN.md, using PLAN-CHECKLIST.md to track your work."

7. **Implementation review.** New session. "Review the implementation of Phase 1 against PLAN.md as a senior engineer." Read its feedback, then tell it to address its own recommendations. Repeat until the phase is clean.

8. **Commit.** Once satisfied with a phase, commit all changes. Pushing is a separate decision — commit to preserve the checkpoint.

Repeat steps 6–8 for each phase.

9. **Final review.** New session. "Review all changes on this branch as a senior engineer." This is a holistic review — the model may catch issues that only emerge when the pieces come together. Have it address the issues. Repeat until all major issues are resolved.

10. **Refactoring (optional).** New session. "Review all changes on this branch and identify high-leverage refactoring opportunities." Save to `REFACTOR_PLAN.md`. Review yourself — not every suggestion is worth pursuing. Then implement in a new session, followed by another review pass. Worth considering when the implementation involved a lot of back-and-forth, touched many files, or introduced patterns that could be cleaned up.

# Related methodologies

This playbook didn't emerge in a vacuum. Several methodologies have converged on similar ideas — separating research, planning, and implementation when working with AI coding agents. Two worth knowing about:

**Research, Plan, Implement (RPI)** is the closest relative. Developed by [Dex Horthy](https://github.com/humanlayer/advanced-context-engineering-for-coding-agents) at HumanLayer, RPI follows the same three-phase structure: research the codebase first, produce a plan, then implement phase by phase. Like this playbook, RPI emphasizes fresh context windows between phases and persisting work as markdown artifacts. Where RPI goes deeper is in **context window management** — Horthy's "Dumb Zone" concept (model performance degrades when context exceeds ~40% capacity) drives the entire workflow design, with explicit compaction points between phases. Where this playbook goes further is in **review cycles** — RPI treats implementation review as optional, while this playbook builds review into every phase transition and adds advanced techniques like cross-model review.

**Spec-Driven Development (SDD)** is broader. Popularized in 2025 by [Thoughtworks](https://www.thoughtworks.com/en-us/insights/blog/agile-engineering-practices/spec-driven-development-unpacking-2025-new-engineering-practices), Amazon's [Kiro IDE](https://kiro.dev), and GitHub's [Spec Kit](https://github.com/github/spec-kit), SDD treats the specification as the primary artifact — code is derived from it, not the other way around. The workflow is similar (Specify → Plan → Task → Implement), but SDD is more formal and tool-oriented. An [arXiv paper by Piskala](https://arxiv.org/html/2602.00180v1) identifies three levels of rigor, from "spec-first" (specs guide development) to "spec-as-source" (specs are the only human-edited artifact, code is fully generated). This playbook shares SDD's "write it down before you code" philosophy but is more lightweight — markdown files and git, no specialized tooling required.

Both methodologies emerged as responses to the same problem: unstructured "vibe coding" with AI agents produces unreliable results. The convergence across independent practitioners and organizations suggests the core insight is sound — **the bottleneck in AI-assisted development isn't code generation, it's ensuring the model understands what to build before it starts building.**

# Tooling

## Branching strategy: git worktrees

Git worktrees let you check out multiple branches into separate directories. This is useful with AI agents because you can run multiple agents in parallel, each on a different feature branch in its own worktree — without them stepping on each other's files.

Instead of the typical branch-switch workflow:
```bash
git checkout -b feature-x    # blocks you from working on anything else
```

Use worktrees:
```bash
git worktree add ../myproject-feature-x feature-x
git worktree add ../myproject-feature-y feature-y
```

Each worktree is a full working directory with its own branch. Open separate terminal sessions, point an agent at each, and have them working on different tasks at the same time. When done, merge as usual and clean up:
```bash
git worktree remove ../myproject-feature-x
```

## Code intelligence: Language Server Protocol (LSP) plugins

Claude Code supports [LSP plugins](https://code.claude.com/docs/en/discover-plugins#code-intelligence) that give the agent the same code intelligence that powers VS Code — jump to definition, find references, and real-time type error detection. After every file edit, the language server analyzes changes and reports errors back automatically, so the agent catches type errors, missing imports, and syntax issues without running a compiler or linter.

**To install:** You need the language server binary on your system, then install the corresponding Claude Code plugin:

```bash
# Example: Python (pyright)
pip install pyright
/plugin install pyright-lsp@claude-plugins-official

# Example: Go
go install golang.org/x/tools/gopls@latest
/plugin install gopls-lsp@claude-plugins-official

# Example: TypeScript
npm install -g typescript-language-server typescript
/plugin install typescript-lsp@claude-plugins-official
```

**Available LSP plugins:**

| Language   | Plugin              | Binary required              |
| :--------- | :------------------ | :--------------------------- |
| C/C++      | `clangd-lsp`        | `clangd`                     |
| C#         | `csharp-lsp`        | `csharp-ls`                  |
| Go         | `gopls-lsp`         | `gopls`                      |
| Java       | `jdtls-lsp`         | `jdtls`                      |
| Kotlin     | `kotlin-lsp`        | `kotlin-language-server`     |
| Lua        | `lua-lsp`           | `lua-language-server`        |
| PHP        | `php-lsp`           | `intelephense`               |
| Python     | `pyright-lsp`       | `pyright-langserver`         |
| Rust       | `rust-analyzer-lsp` | `rust-analyzer`              |
| Swift      | `swift-lsp`         | `sourcekit-lsp`              |
| TypeScript | `typescript-lsp`    | `typescript-language-server` |

**Why this matters with AI agents:**

- **Automatic error detection.** The agent sees type errors and missing imports immediately after editing — no separate compile or lint step needed. If it introduces a bug, it notices and fixes it in the same turn.
- **Precise navigation.** Jump-to-definition and find-references are more accurate than grep-based search, helping the agent understand code structure and dependencies.
- **Fewer broken edits.** Without an LSP, the agent can confidently produce code with subtle type mismatches that only surface at runtime. With one, those errors are caught inline.

## Static analysis: mypy, ruff, and pyright

Static analysis tools catch entire categories of bugs before runtime and give both you and the model a tighter feedback loop during implementation.

**Ruff** replaces flake8, isort, black, and others in a single fast binary. Configure rules via `ruff.toml` or `[tool.ruff]` in `pyproject.toml`.

**Mypy** verifies that type annotations are internally consistent — catching wrong argument types, missing attributes, or incorrect return types that would otherwise only surface at runtime. Adding mypy nudges you toward type annotations, which also gives AI agents better context about function contracts.

**Pyright** (Microsoft's type checker, the engine behind Pylance) is faster than mypy and infers more aggressively, catching issues even in partially annotated code. Some teams run both since they catch slightly different things.

**Why these matter with AI agents:**

- **Faster feedback loops.** Run `ruff check && mypy . && pyright` after each phase and the agent can fix mechanical issues before you review.
- **Fewer silent bugs.** AI agents confidently produce code with subtle type mismatches or incorrect signatures. Static analysis catches these before they become runtime errors.
- **Better AI output.** Type annotations and enforced lint rules give the agent more signal about how to write correct, consistent code.
- **Pre-commit hooks.** Wire all three into pre-commit or CI so nothing gets merged without passing. This automated gatekeeper catches mechanical errors, freeing your reviews to focus on logic and architecture.

# Advanced

## Scaling with multiple agents

The process above uses one agent at a time, switching sessions between stages. This works, but it has two limitations: the same model reviewing its own work tends to share the same blind spots across sessions, and the human is in the loop at every step.

You can address both by distributing work across multiple agents with different roles, models, and permissions.

**Use different models for different roles.** Models trained on different data with different architectures produce largely uncorrelated errors — the same principle behind ensembling in machine learning. Use one model to implement and a different model to review. Where one is consistently weak, the other is often strong. Two strong models usually captures most of the benefit. Focus cross-model review on substance — logic errors, type mismatches, missing edge cases — not formatting opinions.

**Match model capability to task complexity.** Not every stage demands the same level of reasoning. Research, planning, and review require synthesis and judgment. Implementation — guided by a detailed plan — is largely mechanical. Use your strongest model for research, planning, and review; use a faster, cheaper model for implementation. The strong model does the thinking, the fast model does the typing. If the faster model struggles with a particular phase, escalate to the stronger model rather than burning cycles.

**Enforce hard boundaries between agents.** A fresh session resets the context window but not the model's tendencies. Hard boundaries make the reviewer genuinely independent: different models with different failure modes, different permissions (the implementer edits files, the reviewer can only read and flag issues), and automated gates (tests, type checks, linters must pass before the reviewer sees the code). Structured handoffs — where the implementer summarizes what it changed and the reviewer gets that summary plus the diff, not the full conversation history — prevent the reviewer from being anchored by the implementer's reasoning.

**Automate the inner loop, keep humans at the leverage points.** Hard boundaries are what let you safely defer human involvement. With independent agents and automated gates, the human doesn't need to be in the loop for every phase. A more automated workflow:

1. **Research and planning** — Agent produces `RESEARCH.md` and `PLAN.md`. **Human reviews and approves the plan.** (Highest leverage — errors here cascade into everything downstream.)
2. **Implementation loop** — For each phase, the implementer agent executes, automated gates run, and a reviewer agent (different model) reviews against `PLAN.md`. They iterate until the reviewer is satisfied. No human involvement required.
3. **Pull request** — **Human reviews** the cumulative changes as a PR. The artifacts (`RESEARCH.md`, `PLAN.md`, the commit history) become the PR description, giving full visibility into the agent's reasoning.

This reduces human touchpoints from ~12 (every review gate) to ~2 (plan and PR). The key insight: **the more detailed your plan, the more safely you can delegate to autonomous execution.** A plan that says "add authentication" invites the agent to make dozens of unsupervised decisions. A plan that specifies the middleware structure, session handling, and error responses leaves little room to go wrong.

| Plan detail | Safe autonomy level |
| :---------- | :------------------ |
| High-level goal | Human-in-the-loop for every step |
| Phased plan with architecture decisions made | Autonomous per phase, review between phases |
| Detailed plan with file paths and function signatures | Autonomous implementation, human reviews PR |
| Exact specifications with test cases | Fully autonomous with automated verification |

**The tradeoff:** you're trading immediate human oversight for throughput. This works when the plan is detailed enough to constrain the implementation and the automated gates are comprehensive enough to catch regressions. It doesn't work when requirements are fuzzy, the test suite is thin, or the task requires judgment calls the plan didn't anticipate. Start with the fully human-in-the-loop process. Automate the inner loop once you trust your plans and your gates.

## Extended context: 1M context models

Claude Code offers 1M context variants of both Sonnet and Opus via the `/model` command. These models accept up to 1 million tokens of context — roughly 5x the standard 200k window — but are billed at a higher rate for input beyond 200k tokens ($6/$22.50 per Mtok for Sonnet, $10/$37.50 per Mtok for Opus). Note: as of February 2026, 1M context models require API usage and are not available on subscription plans.

Because of the cost, these probably shouldn't be your default — but they can be used strategically.

**A practical approach:**

1. **Use 200k models as your defaults.** They're sufficient for the vast majority of tasks.
2. **Turn off auto-compact** (toggle in `/config`). This lets you see when you're actually hitting context limits rather than silently losing history.
3. **Switch to 1M context when you hit the wall.** If the context limit is reached and you don't have an easy path to `/clear` and pick up where you left off — this can happen during long research sessions — switch to the 1M context model to finish the current task, then start a new session and switch back.

**When 1M context is worth the cost:**

- **Deep research sessions.** Exploring a large, unfamiliar codebase where you need the model to hold many files in memory simultaneously.
- **Complex multi-file refactors.** When the model needs to reason across many files at once and compaction would lose critical details.
- **Long debugging sessions.** When the trail of evidence spans many files and you'd lose important context by compacting or clearing.

For routine implementation, review, and planning work, the standard 200k window with fresh sessions per stage (as described in the process above) is more cost-effective and usually sufficient.
