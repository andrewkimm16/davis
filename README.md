[DAVIS_README.md](https://github.com/user-attachments/files/26225197/DAVIS_README.md)
# DAVIS — Data Access Via Intelligent Search
**Status:** Proof of Concept (personal build) | Greenlit initiative at Genius Sports

---

## The Problem

At Genius Sports, product managers on the Free to Play/Fan Engagement team regularly needed data to answer questions like:

> *"How many users picked the Seahawks to win the Super Bowl in the NFL Bracket Challenge?"*

Getting that answer required one of two things: finding an engineer willing to context-switch and write a SQL query against a legacy PHP-backed database, or waiting for me (the TPM) to pull it myself. Either way, the process involved tickets, back-and-forth, and delays — for what should be a 10-second question.

This is the problem DAVIS is designed to solve: **give non-technical PMs direct access to product data through natural language, with no SQL required.**

---

## The Solution

DAVIS is a lightweight internal analytics tool that accepts plain English questions, translates them into SQL queries, executes them against our product database, and returns a clear, readable result. As an example:

A PM types:
```
How many users picked the Seahawks to win the Super Bowl in the NFL Bracket Challenge?
```

And gets back:
```
1,847 users selected the Seahawks in the NFL Super Bowl Bracket Challenge.
This represents 12.3% of total participants in that activation.
```

No tickets. No engineers. No waiting.

---

## Architecture

```
[User Input]
     │
     ▼
[React Frontend]
  - Text input field
  - Client / product filters
  - Results display
     │
     ▼
[Hugging Face Inference API]
  - Gemini model (enterprise)
  - System prompt containing DB schema context
  - Translates natural language → SQL query
     │
     ▼
[Supabase Backend]
  - Syncs with legacy PHP database via scheduled endpoint
  - Keeps a clean, queryable replica of production data
  - Executes generated SQL query
     │
     ▼
[Results Layer]
  - Raw query results
  - LLM-generated plain English summary
  - Returned to frontend for display
```

---

## Why This Architecture

**Why Supabase instead of querying the legacy DB directly?**

Our production database runs on an older PHP stack. Giving an LLM-generated query direct write or read access to production data introduces risk — a malformed query could be slow, expensive, or destructive. Supabase acts as a clean, read-only replica that stays in sync via a scheduled endpoint, isolating the tool from production risk while keeping data current.

**Why Hugging Face + Gemini?**

Genius Sports was already running Google's enterprise Gemini model internally, so using it here kept us within existing security and data governance boundaries. Hugging Face provided a clean inference API layer that made the integration straightforward to prototype without full backend infrastructure.

**Why a simple chat UI?**

The users are non-technical PMs. The lowest friction interface for natural language input is a chat box — it's a mental model they already have from tools like ChatGPT. Adding client and product filters reduces ambiguity in the query without requiring users to specify those parameters in their natural language input every time.

---

## Key Technical Decisions & Tradeoffs

| Decision | Alternative Considered | Why I Chose This |
|---|---|---|
| Supabase replica | Direct legacy DB access | Production safety, cleaner schema, easier to iterate |
| Gemini via Hugging Face | OpenAI GPT-4 | Already enterprise-approved, no new vendor approval needed |
| Chat UI with filters | Full freeform text only | Reduces prompt ambiguity without adding friction |
| Read-only query execution | Full CRUD access | Eliminates risk of data mutation from generated queries |
| Plain English summary layer | Raw query results only | Non-technical users need interpretation, not just data |

---

## Example Queries

These are real questions PMs on my team asked manually — the kind of requests this tool is designed to handle:

```
How many users played PGA TOUR Fantasy last week?
What was the week-over-week retention rate for Jersey Mike's NHL PickEM in Q4?
How many unique users participated in the NFL Bracket Challenge?
Which product had the highest DAU across all MLB Play products last month?
What percentage of CFL All-Stars users returned the following week?
```

---

## What I Built (POC)

While at Genius, I was building a working prototype independently — no engineering support. Progress included:

- Supabase project configured with schema mirroring our core engagement tables
- Hugging Face inference endpoint connected to Gemini with a system prompt containing DB schema context
- Basic React frontend with text input and client/product filter dropdowns
- Manual mapping of data tables and fields to metric descriptions
- End-to-end flow working for simple single-table queries
- Identified edge cases: ambiguous product names across clients, queries spanning multiple tables, handling "no results" gracefully

---

## What's Left

- Multi-table JOIN handling for cross-product queries
- Query validation layer to catch malformed SQL before execution
- Result caching for repeated common queries
- Access controls — not all PMs should see all client data
- Audit logging — visibility into what queries are being run and by whom

---

## What This Taught Me

Building this POC myself — without engineering support — forced me to make real technical decisions rather than just specifying requirements. I learned where the failure modes actually live (schema ambiguity is the hardest problem, not the NL-to-SQL translation itself), which made me a significantly better technical partner when working with engineers on scoping the full build. Building this solo also gave me firsthand experience with AI-assisted development. Using LLMs as a coding collaborator and understanding where they accelerate work and where they introduce risk added a dimension to my AI product thinking that purely theoretical knowledge couldn't.

The most important product insight: **the hard problem isn't the AI. It's data quality and schema clarity.** A well-structured schema with consistent naming conventions produces dramatically better query results than a messy one, regardless of the model used. This became the first item on the full engineering roadmap.

---

## Context

This project was greenlit at Genius Sports as an internal product initiative. I was the sole product owner — responsible for vision, architecture decisions, requirements, and the personal POC build.

---

*DAVIS — Built by Andrew Kim — Technical Product Manager*
*andrewkimm16@gmail.com | [LinkedIn](www.linkedin.com/in/andrew-taewook-kim-62039620b)*
