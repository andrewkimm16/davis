[DAVIS_README.md](https://github.com/user-attachments/files/26225197/DAVIS_README.md)
# DAVIS — Data Access Via Intelligent Search
**Status:** Proof of Concept (personal build) | Greenlit initiative at Genius Sports

---

## The Problem

At Genius Sports, product managers regularly needed data to answer questions like:

> *"How many users picked the Seahawks to win the Super Bowl in the NFL Bracket Challenge?"*

Getting that answer required one of two things: finding an engineer willing to context-switch and write a SQL query against a legacy PHP-backed database, or waiting for me (the TPM) to pull it myself. Either way, the process involved tickets, back-and-forth, and delays, for what should be a 10-second question.

Worse, when answers did come back, definitions varied across queries. Different engineers interpreted ambiguous field names differently, leading to inconsistent reporting and eroding PM trust in the data. The problem was not only just speed, but also reliability.

This is the problem DAVIS is designed to solve: **give non-technical PMs direct, consistent access to product data through natural language, with no SQL required.**

---


## The Solution

DAVIS is a lightweight internal analytics tool that accepts plain English questions, translates them into SQL queries using a schema-grounded LLM, executes them against a replicated product database, and returns a clear, readable result.

The key word is **schema-grounded**: rather than letting the LLM generate SQL from scratch, DAVIS constrains it to a structured schema context, including valid tables, column names, and data types, which dramatically reduces hallucinated joins and invalid field references. The LLM isn't guessing at database structure; it's working within a defined boundary.

A PM types:
```
How many users picked the Seahawks to win the Super Bowl in the NFL Bracket Challenge?
```

And gets back:
```
1,847 users selected the Seahawks in the NFL Super Bowl Bracket Challenge.
This represents 12.3% of total participants in that activation.
```

This simple response reduces a chronic bottleneck of time, resources, and inconsistency.

---

## Architecture

```
[User Input — Plain English Question]
          │
          ▼
[React Frontend]
  - Text input field
  - Client / product filter dropdowns
  - Results display panel
          │
          ▼
[Schema-Grounded LLM Layer]
  - Google Gemini (enterprise access)
  - System prompt contains full DB schema context
  - Constrains generation to valid tables and fields
  - Translates natural language → valid PostgreSQL
          │
          ▼
[Query Execution Layer — Guardrailed]
  - Read-only access enforced
  - Queries routed through secure RPC wrapper
  - Prevents destructive operations
  - Enforces row-level constraints per client/product
          │
          ▼
[Supabase Replica DB]
  - Syncs with legacy PHP database via scheduled endpoint
  - Clean, queryable replica isolated from production risk
  - Executes validated SQL query
          │
          ▼
[Results Summarization Layer]
  - Raw results passed back to LLM
  - Returns plain English summary for non-technical audience
  - Displayed in frontend
```

---

## Why This Architecture

**Why a Supabase replica instead of querying production directly?**

Our production database runs on an older PHP stack. Giving an LLM-generated query direct access to production data introduces risk. A malformed query could be slow, expensive, or destructive. Supabase acts as a clean, read-only replica that stays in sync via a scheduled endpoint, isolating the tool from production risk while keeping data current.

**Why schema-grounded generation instead of pure NL-to-SQL?**

Unconstrained LLMs hallucinate column names and invent joins between tables that don't exist. By embedding the full DB schema in the system prompt, DAVIS constrains the LLM to what's actually there, which dramatically improves query accuracy and reducing the need for human validation of generated SQL.

**Why a guardrailed query execution layer?**

Even with schema grounding, generated SQL needs a safety net. Queries are routed through a secure server-side RPC function that enforces read-only access and client-level data boundaries. This waas a critical production requirement. We had clients with protected data rights, and without it, a malformed query could touch data it shouldn't.

**Why Google Gemini?**

Genius Sports was already running Google's enterprise Gemini model internally, so using it here kept the prototype within existing security and data governance boundaries, whic meant no new vendor approval was required.

**Why a simple chat UI?**

The users are non-technical PMs. The lowest-friction interface for natural language input is a chat box, which is a mental model they already have. Adding client and product filter dropdowns reduces query ambiguity without requiring users to specify those parameters in natural language every time, while also focusing and constraining the AI search.

---

## Key Technical Decisions & Tradeoffs

| Decision | Alternative Considered | Why I Chose This |
|---|---|---|
| Supabase replica | Direct legacy DB access | Production safety, cleaner schema, isolated risk |
| Schema-grounded generation | Pure NL-to-SQL without context | Reduces hallucinated joins and invalid field references |
| Guardrailed RPC execution | Direct query execution | Prevents destructive operations, enforces access control |
| Gemini via enterprise access | OpenAI GPT-4 | Already approved internally, no new vendor process |
| Chat UI with filters | Full freeform text only | Reduces prompt ambiguity without adding friction |
| Plain English summary layer | Raw query results only | Non-technical users need interpretation, not just data |

---

## Example Queries

These are real questions PMs on my team asked manually and the kind of requests DAVIS is designed to handle:

```
How many users played PGA TOUR Fantasy last week?
What was the week-over-week retention rate for Jersey Mike's NHL PickEM in Q4?
How many unique users participated in the NFL Bracket Challenge?
Which product had the highest DAU across all MLB Play products last month?
What percentage of CFL All-Stars users returned the following week?
```

---

## What I Built (POC)

While at Genius, I was building a working prototype independently and without engineering support. Progress included:


- Supabase project configured with schema mirroring our core engagement tables
- Gemini connected with a schema-grounded system prompt
- Basic React frontend with text input and client/product filter dropdowns
- Manual mapping of data tables and fields to metric descriptions
- End-to-end flow working for simple single-table queries
- Identified edge cases: ambiguous product names across clients, queries spanning multiple tables, handling "no results" gracefully


---

**A note on this repository:**

After losing access to internal systems, I rebuilt a simplified standalone version to demonstrate the core interaction loop: NL input → schema-grounded SQL generation → guardrailed execution → plain English result. This version uses a generic schema and mock execution layer, but reflects the same architectural patterns, tradeoffs, and design decisions as the original internal prototype.

The gaps between this demo and a production system are intentional and documented below and they represent the roadmap. 

---

## Next Phase: Productionizing the System

The POC validated the core interaction loop. Moving to production requires:

**Query Validation Layer** — Catch malformed SQL before it reaches the database. Validate generated queries against schema constraints before execution, with a fallback to plain-language error explanation for the user.

**Canonical Data Model** — The hardest problem in this system isn't the AI. It's data quality and schema clarity. Inconsistent field naming across our legacy products means the same concept (e.g., "active user") is stored differently across tables. A canonical model layer that normalizes these definitions before query generation is the most critical production investment.

**Access Controls** — Not all PMs should see all client data. Row-level security policies in Supabase would enforce client-level data boundaries automatically.

**Audit Logging** — Full visibility into what queries are being run, by whom, and when. Essential for data governance and debugging unexpected results.

**Result Caching** — Common queries (weekly DAU, retention rates) could be cached to reduce LLM and DB load.

---

## What This Taught Me

Building this POC myself forced me to make real technical decisions rather than just specifying requirements. I learned where the failure modes actually live (schema ambiguity is the hardest problem, not the NL-to-SQL translation itself), which made me a significantly better technical partner when working with engineers on scoping the full build. Building this solo also gave me firsthand experience with AI-assisted development and vibe coding. Using LLMs as a coding collaborator and understanding where they accelerate work and where they introduce risk added a dimension to my AI product thinking that purely theoretical knowledge couldn't.

The most important product insight: **the hard problem isn't the AI. It's data quality and schema clarity.** A well-structured schema with consistent naming conventions produces dramatically better query results than a messy one, regardless of the model used. This became the first item on the full engineering roadmap.

---

## Context

This project was greenlit at Genius Sports as an internal product initiative. I was the sole product owner and was responsible for vision, architecture decisions, requirements, and the personal POC build. This repository is a standalone reconstruction of that work, built to demonstrate the architectural thinking and interaction loop rather than the full production system.

---

*DAVIS — Built by Andrew Kim — Technical Product Manager*
*andrewkimm16@gmail.com | [LinkedIn](www.linkedin.com/in/andrew-taewook-kim-62039620b)*
