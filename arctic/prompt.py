"""Arctic-Text2SQL-R1-7B prompt, verbatim from Snowflake's own evaluation code
(snowflakedb/ArcticTraining, projects/arctic_text2sql_r1/bird_eval/infer.py; = Figure C.1 of arXiv:2505.20315):
system + user message rendered with the Qwen2.5 chat template (apply_chat_template, add_generation_prompt=True),
then the assistant turn is pre-filled with "Let me solve this step by step. \\n<think>". The SQL is the LAST ```sql
block of the completion (their parse_response). Greedy decoding (temperature 0) as in their non-self-consistency eval.

Two deliberate substitutions, both in slots the template provides:
  * "Database Engine:" PostgreSQL instead of SQLite (the bench executes on Postgres 16.4; the card's prompt names the
    engine of the target database);
  * "Database Schema:" the 11 Chinook CREATE TABLE statements in vanna/training/ddl.sql (information_schema +
    pg_constraint via the read-only role; the same DDL Vanna was trained on). No sample values, no comments, no
    benchmark questions or gold SQL. Nothing else is added (no evidence/hints)."""
import pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DDL = (ROOT / "vanna" / "training" / "ddl.sql").read_text().strip()
ENGINE = "PostgreSQL"
SYSTEM = ("You are a data science expert. Below, you are provided with a database schema and a natural"
          " language question. Your task is to understand the schema and generate a valid SQL query to"
          " answer the question.")
COT_PREFILL = "Let me solve this step by step. \n<think>"
INSTRUCT = """
Please provide a detailed chain-of-thought reasoning process and include your thought process within `<think>` tags. Your final answer should be enclosed within `<answer>` tags.

Ensure that your SQL query follows the correct syntax and is formatted as follows:

```sql
-- Your SQL query here
```

Example format:
<think> Step-by-step reasoning, including self-reflection and corrections if necessary. [Limited by 4K tokens] </think>
<answer> Summary of the thought process leading to the final SQL query. [Limited by 1K tokens]

```sql
Correct SQL query here
```
</answer>""".strip()


def user_message(question, schema=DDL, engine=ENGINE):
    return f"""
Database Engine:
{engine}

Database Schema:
{schema}
This schema describes the database's structure, including tables, columns, primary keys, foreign keys, and any relevant relationships or constraints.

Question:
{question}

Instructions:
- Make sure you only output the information that is asked in the question. If the question asks for a specific column, make sure to only include that column in the SELECT clause, nothing more.
- The generated query should return all of the information asked in the question without any missing or extra information.
- Before generating the final SQL query, please think through the steps of how to write the query.

Output Format:
{INSTRUCT}
    """.strip()


def build_prompt(question):
    """Raw prompt string = Qwen2.5 chat template (system + user, add_generation_prompt) + the CoT prefill."""
    return (f"<|im_start|>system\n{SYSTEM}<|im_end|>\n"
            f"<|im_start|>user\n{user_message(question)}<|im_end|>\n"
            f"<|im_start|>assistant\n{COT_PREFILL}")


def parse_sql(completion):
    """Last ```sql block (Snowflake's parse_response); '' if none."""
    blocks = re.findall(r"```sql\s*(.*?)\s*```", completion, re.DOTALL)
    return blocks[-1].strip() if blocks else ""
