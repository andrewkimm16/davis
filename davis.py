"""
DAVIS — Data Access Via Intelligent Search
Proof of Concept | Built by Andrew Kim

A lightweight internal analytics tool that accepts plain English questions
from non-technical PMs, translates them into SQL queries using an LLM,
executes them against a product database, and returns a readable summary.

Architecture:
    User Input → LLM (Gemini) → SQL Query → Supabase → Plain English Result

Dependencies:
    pip install google-generativeai supabase python-dotenv

Environment Variables (.env):
    GEMINI_API_KEY=genius_key
    SUPABASE_URL=supabase_url
    SUPABASE_KEY=supabase_key
"""

import os
import json
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL   = os.getenv("SUPABASE_URL")
SUPABASE_KEY   = os.getenv("SUPABASE_KEY")

# ---------------------------------------------------------------------------
# DATABASE SCHEMA CONTEXT - FOR SAMPLE TESTING IN PHASE 1
# Passed to the LLM so it understands the structure of our data.
# In production this would be generated dynamically from Supabase metadata.
# ---------------------------------------------------------------------------

DB_SCHEMA = """
You have access to a product analytics database with the following tables:

TABLE: user_events
  - event_id        (uuid)        Unique identifier for the event
  - user_id         (uuid)        Unique identifier for the user
  - product_slug    (text)        e.g. 'pga-tour-fantasy', 'nfl-bracket-challenge', 'bww-pick-a-side'
  - client_slug     (text)        e.g. 'pga-tour', 'nfl', 'buffalo-wild-wings'
  - event_type      (text)        e.g. 'session_start', 'pick_submitted', 'lineup_saved'
  - event_data      (jsonb)       Flexible payload — e.g. {"team_picked": "Seahawks", "round": "super_bowl"}
  - created_at      (timestamptz) When the event occurred

TABLE: users
  - user_id         (uuid)        Unique identifier
  - created_at      (timestamptz) When the user registered
  - last_active_at  (timestamptz) Most recent activity timestamp
  - client_slug     (text)        Which client this user belongs to

TABLE: weekly_active_users
  - week_start      (date)        Monday of the week
  - product_slug    (text)        Which product
  - client_slug     (text)        Which client
  - wau_count       (integer)     Number of unique active users that week
  - retention_rate  (float)       % of users who returned from the prior week

TABLE: products
  - product_slug    (text)        Unique identifier e.g. 'pga-tour-fantasy'
  - product_name    (text)        Display name e.g. 'PGA TOUR Fantasy'
  - client_slug     (text)        Which client owns this product
  - is_active       (boolean)     Whether the product is currently live

Only return valid PostgreSQL. Do not include markdown formatting or code fences.
Only return the SQL query itself — nothing else.
"""

# ---------------------------------------------------------------------------
# MOCK MODE
# When real API keys are not present, DAVIS runs in mock mode and returns
# a simulated response so the flow can be demonstrated end-to-end.
# ---------------------------------------------------------------------------

MOCK_RESPONSES = {
    "default_sql": (
        "SELECT COUNT(DISTINCT user_id) AS user_count "
        "FROM user_events "
        "WHERE product_slug = 'nfl-bracket-challenge' "
        "AND event_type = 'pick_submitted' "
        "AND event_data->>'team_picked' = 'Seahawks' "
        "AND event_data->>'round' = 'super_bowl';"
    ),
    "default_result": [{"user_count": 1847}],
    "default_summary": (
        "1,847 users picked the Seahawks to win the Super Bowl in the "
        "NFL Bracket Challenge — representing 12.3% of total participants "
        "in that activation."
    )
}

# ---------------------------------------------------------------------------
# STEP 1 — TRANSLATE NATURAL LANGUAGE TO SQL
# ---------------------------------------------------------------------------

def generate_sql(question: str, mock: bool = False) -> str:
    """
    Send the user's plain English question to Gemini along with the DB schema.
    Returns a SQL query string.
    """
    if mock:
        print("[DAVIS] Mock mode: generating SQL without API call.")
        return MOCK_RESPONSES["default_sql"]

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-pro")

        prompt = f"""
You are a SQL expert helping a product analytics team query their database.

Here is the database schema:
{DB_SCHEMA}

Translate the following question into a valid PostgreSQL query.
Return only the SQL — no explanation, no markdown, no code fences.

Question: {question}
"""
        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        print(f"[DAVIS] LLM error: {e}")
        print("[DAVIS] Falling back to mock SQL.")
        return MOCK_RESPONSES["default_sql"]


# ---------------------------------------------------------------------------
# STEP 2 — EXECUTE SQL AGAINST SUPABASE
# ---------------------------------------------------------------------------

def execute_query(sql: str, mock: bool = False) -> list:
    """
    Run the generated SQL query against the Supabase database.
    Returns a list of result rows.
    """
    if mock:
        print("[DAVIS] Mock mode: returning simulated query results.")
        return MOCK_RESPONSES["default_result"]

    try:
        from supabase import create_client
        client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Supabase's Python client uses rpc for raw SQL execution.
        # In production, this would use a secure server-side function
        # to prevent injection and enforce read-only access.
        response = client.rpc("execute_safe_query", {"query": sql}).execute()
        return response.data

    except Exception as e:
        print(f"[DAVIS] Database error: {e}")
        print("[DAVIS] Falling back to mock results.")
        return MOCK_RESPONSES["default_result"]


# ---------------------------------------------------------------------------
# STEP 3 — SUMMARIZE RESULTS IN PLAIN ENGLISH
# ---------------------------------------------------------------------------

def summarize_results(question: str, sql: str, results: list, mock: bool = False) -> str:
    """
    Take the raw query results and ask the LLM to summarize them
    in plain English for a non-technical PM audience.
    """
    if mock:
        print("[DAVIS] Mock mode: returning simulated summary.")
        return MOCK_RESPONSES["default_summary"]

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-pro")

        prompt = f"""
A product manager asked the following question:
"{question}"

The SQL query that was run:
{sql}

The results returned:
{json.dumps(results, indent=2)}

Write a clear, concise plain English summary of these results for a non-technical
product manager. Be specific with numbers. Keep it to 1-2 sentences.
"""
        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        print(f"[DAVIS] Summarization error: {e}")
        return f"Query returned: {results}"


# ---------------------------------------------------------------------------
# CORE DAVIS FLOW
# ---------------------------------------------------------------------------

def ask(question: str, client_filter: str = None, product_filter: str = None) -> None:
    """
    Main entry point for DAVIS.

    Args:
        question:       Plain English question from the PM
        client_filter:  Optional — narrow results to a specific client (e.g. 'nfl')
        product_filter: Optional — narrow results to a specific product (e.g. 'nfl-bracket-challenge')

    Example:
        ask("How many users picked the Seahawks to win the Super Bowl?",
            client_filter="nfl",
            product_filter="nfl-bracket-challenge")
    """

    # Determine whether to use mock mode based on env var availability
    mock_mode = not (GEMINI_API_KEY and SUPABASE_URL and SUPABASE_KEY)

    if mock_mode:
        print("\n[DAVIS] Running in demo mode (no API keys detected).")
        print("[DAVIS] Connect a Gemini API key and Supabase instance to run live.\n")

    # Append filter context to the question if provided
    context_note = ""
    if client_filter:
        context_note += f" Limit results to client '{client_filter}'."
    if product_filter:
        context_note += f" Limit results to product '{product_filter}'."

    enriched_question = question + context_note

    print(f"❓ Question: {question}")
    if client_filter or product_filter:
        print(f"   Filters applied: client={client_filter}, product={product_filter}")
    print()

    # Step 1: Generate SQL
    print("⚙️  Generating SQL query...")
    sql = generate_sql(enriched_question, mock=mock_mode)
    print(f"\n   Generated SQL:\n   {sql}\n")

    # Step 2: Execute query
    print("🔍 Executing query...")
    results = execute_query(sql, mock=mock_mode)
    print(f"   Raw results: {results}\n")

    # Step 3: Summarize
    print("📊 Summarizing results...")
    summary = summarize_results(question, sql, results, mock=mock_mode)

    print("\n" + "─" * 60)
    print(f"✅ DAVIS Answer:\n\n   {summary}")
    print("─" * 60 + "\n")


# ---------------------------------------------------------------------------
# EXAMPLE USAGE
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    # Example 1: The question that started it all
    ask(
        question="How many users picked the Seahawks to win the Super Bowl?",
        client_filter="nfl",
        product_filter="nfl-bracket-challenge"
    )

    # Example 2: Weekly active users check
    # ask(
    #     question="What was the average WAU for PGA TOUR Fantasy last month?",
    #     client_filter="pga-tour",
    #     product_filter="pga-tour-fantasy"
    # )

    # Example 3: Retention check
    # ask(
    #     question="What was the week-over-week retention rate for BWW Pick a Side last quarter?",
    #     client_filter="buffalo-wild-wings",
    #     product_filter="bww-pick-a-side"
    # )
