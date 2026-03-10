---
title: "Build Capabilities, Not Factories: Lessons from Building a Deep Research Agent"
date: 2026-03-09
description: |
  I built two deep research systems for AI agents: a multi-phase pipeline that took months, and a set of four CLI tools plus a prompt that took a weekend. I'm now convinced the simpler system is better.
options:
  categories:
    - AI
    - software-engineering
    - claude-code
    - LLM
    - deep-research

---

I built two custom "deep research" systems for AI agents. One took months: a multi-phase pipeline implemented as an MCP server with 10,000+ lines of Python code and dozens of configuration parameters. The second was implemented as a Claude Code skill and took barely a weekend: four CLI tools, and a few prompts. After using each of these tools, I'm convinced the simpler system is better.

In this post I'll talk through the journey I've been on in developing these tools, and what I've learned.

# The research process

As a Research Scientist, I'm deeply familiar with the process *of research*: You have a question like "What do we know about behavioral interventions that can promote frustration tolerance?" or "Does AI tutoring really work and what evidence do we have?".

To answer questions like these, you go to *The Literature*. You search Google, Google Scholar, Arxiv, Web of Science, etc. You find as many sources as you can for different variations on your question. You sift through the pile of sources to find the ones that are most relevant and most credible. Then you read them, one by one. Sometimes you chase down more sources as you see the same citations pop up in one paper, and then another. The research "snowballs" but eventually you have to stop --  stop and you synthesize what you've read; bring what you've read to bear on the questions you started with, as well as the questions that occurred to you while you were on the journey of discovery.

My familiarity with the research process has given me an affinity for "Deep Research" tools popularized by Google, Anthropic, and OpenAI.

I also have a deep affinity for DIY, and when I saw [LangChain's own Open Deep Research tool](https://github.com/langchain-ai/open_deep_research) -- an open-source tool that was able to go toe-to-toe with Google's or Anthropics (according to the [DeepResearch Bench Leaderboard](https://huggingface.co/spaces/muset-ai/DeepResearch-Bench-Leaderboard)), ***I was inspired.*** I decided to build my own deep research tool, fitted for the academic research use cases that I had in mind.

Towards the end of 2025 I started hacking away on the odd evening or weekend afternoon. By February, I'd built a tool modeled after LangChain's own. Then I started down the path of customizing it: I wanted it to fetch sources from Semantic Scholar, find their DOIs using Citeref, prioritize sources by citation count or other source credibility factors. I wanted it to generate a report with high-quality inline citations and a "references" section, and to double-check every claim against the sources to which the claim was attributed. I was buzzing with ideas for features that seemed necessary to get output that would rise to the standards of an academic researcher.

This customization took a few more weeks. I finally got to a point where I could test it. I asked a colleague to tell me an area in which they were deeply familiar so I could run it through the tool and they could judge. It was *pretty good*, but not *great*. I tested it myself by generating a report in an area I know really well from graduate studies -- the "psychology of the uncanny valley". Again, it was *pretty good*, but not *great*.

I identified weaknesses, and I tried to fix the system by adding more stages, more config, more heuristics. I added a source verification step. I added intermediate summarization steps. I added heuristics for identifying "claims" in the paper and flagging them as "unsupported," "contradicted," or "supported," with actions attached to each. I tuned the supervision loop. Each fix helped a little but added complexity. It was hard to observe what was happening inside the black box. So I added observability features: Record every step and sub-step for review later. It was still opaque. After a dozen or more iterations, I had a nagging feeling that I was just treating symptoms, and barely moving the needle. It occurred to me that my assumptions might be wrong -- that maybe a pre-defined workflow, followed step-by-step, in which a *system* would make decisions using an increasingly complex web of rules and branching conditions -- might not be the best approach.

# Something changed

There's a time before November 2025 and there's a time after.

Before November 2025, language models' agentic capabilities were nascent. If you had a complex workflow for a language model to perform, you needed to build scaffolding to keep it on the happy path. Without scaffolding, the model could not be trusted. The model would skip steps, generate the wrong kind of output structure, or simply make bad decisions. Encoding a complex workflow *in code*, putting the model *on rails*, seemed to be the only way to get any reliability at all.

Then at the end of November 2025 Opus 4.5 launched, and a few weeks later GPT 5.2 followed.

Something changed. I'm not the only one who's noticed.

I watched an episode of Hard Fork in which Amanda Askell described how Anthropic approached alignment for [Claude's new constitution](https://www.youtube.com/watch?v=Zj35mEtwUvY): instead of giving Claude rules to follow, Anthropic would teach Claude about the "values" it should embody. In other words, they would instruct Claude not just *what to do* or *how to do it*, but *why*. This was important because, as she argued, rules are fragile and don't generalize very well to novel situations. Dr. Askell argued that we needed to *trust* the models more to reason from principles.

More recently, I read Aaron Tay's [evaluation of academic research tools](https://aarontay.substack.com/p/creating-your-own-research-assistant). He provided evidence that general-purpose agents like Claude, equipped with simple web search tools, could do just as well as specialized tools like Consensus Deep Search. He gave anecdotes in which these bespoke tools would fail when encountering situations that the designers hadn't anticipated, whereas Claude would handle the situation amicably and return more relevant information. He ended his piece with a thought that stuck with me: "[does] the future of research tooling lie in polished, vendor-defined products or in researcher-configured composable environments?"

I wasn't the only one rethinking how I was working with AI. Simon Willison [called](https://simonwillison.net/2026/Jan/4/inflection/) November 2025 an inflection point -- "one of those moments where the models get incrementally better in a way that tips across an invisible capability line."

It was around this time that Boris Cherny, the creator of Claude Code, is also said to have coined the ["6 month rule"](https://tdhopper.com/blog/build-for-the-model-six-months-from-now/): (a restatement of the [Bitter Lesson](http://www.incompleteideas.net/IncIdeas/BitterLesson.html)): "Don't build for the model of today, build for the model 6 months from now".

Over a weekend in March, I rebuilt my custom deep research tool as a Claude Code "skill": four CLI tools and a few prompts. I was surprised to find that it performed just as well as the complex and rigid pipeline that took months to build earlier. I had learned the bitter lesson myself.

# The two approaches

I think it's fair to describe my initial attempt at designing a deep research system as a ***factory***, and my second attempt as a set of ***capabilities***.

In a factory, the agent acts as a **caller** to a **pipeline**. The agent submits a query, polls for status until it's complete, and retrieves a finished output. The real work happens inside code that the agent can't see or influence. The agent is a client placing an order.

Capabilities treat the agent as a **thinker**. The agent decides what to search, when to stop, what to read deeply, how to synthesize. The agent is a researcher with tools on its desk.

|              | **Capability (Skill + CLI)**                     | **Factory (MCP tool)**                                       |
| ------------ | ------------------------------------------------ | ------------------------------------------------------------ |
| Agent's role | Supervisor makes every decision                  | Client submits query, waits for result                       |
| Architecture | Four composable CLI tools + orchestrating prompt | Monolithic workflow with hard-coded phases                   |
| Flexibility  | Agent improvises based on what it finds          | Fixed sequence: Clarification → Search → Summarization → Synthesis → Validation |
| Codebase     | A few small CLIs, a few prompts, and some tests  | ~10,000+ lines of Python, dozens of configuration parameters |

# Capability-based deep research

My capability-based deep research tool gives the agent four tools: `search`, `state`, `download`, and `enrich`. That's it. Search can query different providers and returns structured JSON. State tracks sessions, sources, findings, and gaps in a SQLite database. Download fetches PDFs and saves them to LLM-optimized markdown files. Enrich resolves DOI metadata.

The orchestration lives in a ~500-line prompt that outlines an opinionated research methodology: Surface assumptions before you start, fan out by querying different search providers, save full texts, chase citations on key papers, track contradictions, audit source coverage before synthesizing. For context management, I'm now starting to write subagents for tasks like summarizing an article -- this is just another prompt.

This is all presented in the form of guidance, not rigidly enforced control flow. The agent knows what a good research process looks like, but it follows it ***creatively***.

The tools themselves are stateless and composable. The agent can run searches in parallel, download multiple PDFs at once, enrich a batch of DOIs. The tools don't interfere with each other. Every command returns a JSON response, some write to files that the model is instructed to list within the JSON response. State flows through SQLite so the tools are loosely coupled. Adding a new search provider is fairly trivial. Reasoning about the system is easy.

# Factory-based deep research

My factory-based deep research tool looked like this:

1. `research(action="deep-research", query="...")` -- kick off the research job
2. `research(action="deep-research-status", research_id="...")` -- poll status until done
3. `research(action="deep-research-report", research_id="...")` -- retrieve the final report

Everything between steps 1 and 3 was a black box. The agent submitted a query and waited. Inside, the workflow ran through hard-coded phases. The supervision loop -- Think, Delegate, Execute, Assess, Repeat -- was fixed.

The system made up for rigidity with configuration. Dozens of fields controlling timeouts, concurrency, provider fallback order, token budgets, per-phase model routing. Every time the pipeline did something I didn't like, my instinct was to add a bit more complexity.

All that complex machinery exists because the system, not the agent, is designed to make the research decisions. When you take agency away from the agent, you have to build all possible strategies into the system itself. Inevitably, you will fail to cover unanticipated edge cases.

# What I observed

I ran both systems on the same queries. I haven't run any sort of formal evaluation, but when I generate a deep research report in an area that I know deeply (like the "uncanny valley"), I can immediately tell if it's right or wrong. I found that the capabilities researcher produced reports that were at least as good, if not better, than the factory researcher. And the system was an order of magnitude easier to reason about, observe, and iterate on.

# The design principle

If I may be so bold, I think this captures the contrast between factories and capabilities:

***Build tools that extend what an agent can do, not systems that replace what an agent can think.***

In other words, agentic systems should be equipped with tools, and empowered to think and make micro-decisions in the execution of well-defined tasks.

A capability is a means to take certain kinds of actions -- `search`, `download`, `track` -- where each action returns structured data the agent can reason about. It's composable: you can combine capabilities in ways the developer didn't anticipate. It's simple enough that the interface *is* the documentation.

A factory is a multi-step workflow designed as a pipeline. It takes an input, runs a fixed process, and returns a finished product. It's monolithic -- you use all of it or none. And it's complex.

Factories are harder to build and less capable in the hands of today's agents than an equivalent set of tools paired together with a good prompt that provides task guidance. The tools+prompt pattern leverages the agent's intelligence. The factory tries to systematize and replace it.

# Teaching why, not what

There is a similar lesson in how the prompts themselves should be written.

The factory instinct in prompting is to specify every step: search these providers in this order, then download the top five results, then summarize each one, then synthesize. But what if after downloading the top five results, more questions surface that deserve to be investigated? What if the initial queries returned tangential results and the search strategy needs to be revisited? What if one of the sources turns out to be a gold mine for citation chasing to find more and better sources?

The capability approach is to teach the agent ***why***. Not "search Semantic Scholar first" but "academic databases give you structured metadata and citation graphs, which help you find the most influential work." Not "always chase citations" but "citation chasing finds related work that keyword searches miss, especially for niche topics."

This is the same insight from Anthropic's constitution work that got me rethinking in the first place. Rules are brittle. Understanding is robust. A model that knows *why* a behavior matters will handle novel situations. A model that memorized a list of dos and don'ts won't.

This only works when the model is smart enough to reason from principles. A year ago, "teach it why" would have been bad advice. At best this would have been irrelevant context, at worst it would have just distracted the model. But today's models seem to benefit from knowing why they're being asked to do things a certain way -- how do actions connect back to the overarching task objective and the needs or wants of the user?

# When factories are appropriate

This isn't absolute. Factories are the right call in some cases.

**When the agent can't be trusted.** My MCP-based deep research pipeline was the right design at the end of 2025. The models weren't reliable enough to orchestrate a 10+ step research workflow without losing the thread. If you're building for models that skip steps or forget what they've tried, encoding the workflow in code is a reasonable safety net. This is still true for smaller, cheaper models -- not everything runs on Opus 4.6 or GPT-5.4. If your system needs to work with Haiku or GPT-4o mini, a factory might be the only way to get reliable results. There's a middle path, too: use a capable model for orchestration and cheaper models for the leaf tasks. You get the flexibility of the capability approach without paying frontier prices for every search summary.

**When latency matters more than quality.** An agent deliberating over what to search next is slower than a pipeline that fires all searches in parallel according to a fixed plan. If you need results in 30 seconds and "good enough" is fine, a factory wins. The skill approach trades latency for adaptability -- the agent might take longer, but it adjusts to what it finds.

# What I took away

I started this project trying to build the perfect research engine. I ended up learning something about how to build for the future of agentic systems.

The pipeline took months and produced results that were *pretty good*, but not *great*. The skill took a weekend and produced results that were just as good -- and I'm now in a position to more quickly and more confidently inch my way towards *great*.

Build capabilities, not factories. Teach agents *why*, not just *what*. Give agents the same tools that you would want to perform the task. And trust the models more than you think you should -- maybe they'll surprise you.
