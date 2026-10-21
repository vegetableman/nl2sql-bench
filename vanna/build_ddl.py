"""Builds Vanna's training material: one CREATE TABLE per Chinook table, from information_schema (columns, types,
nullability) plus primary/foreign keys from pg_constraint, via the read-only bench role. No questions, no gold SQL, no comments
(the database has none). Output: vanna/training/ddl.sql (one statement per table, separated by blank lines)."""
import os, pathlib, psycopg2

conn = psycopg2.connect(os.environ["BENCH_DB_URL"]); cur = conn.cursor()
cur.execute("select table_name from information_schema.tables where table_schema='public' and table_type='BASE TABLE' order by 1")
out = []
for (t,) in cur.fetchall():
    cur.execute("""select column_name, data_type, character_maximum_length, numeric_precision, numeric_scale, is_nullable
                   from information_schema.columns where table_schema='public' and table_name=%s order by ordinal_position""", (t,))
    cols = []
    for c, dt, ml, np_, ns, nl in cur.fetchall():
        typ = {"character varying": f"VARCHAR({ml})" if ml else "VARCHAR", "numeric": f"NUMERIC({np_},{ns})" if np_ else "NUMERIC",
               "timestamp without time zone": "TIMESTAMP", "integer": "INTEGER"}.get(dt, dt.upper())
        cols.append(f"    {c} {typ}{' NOT NULL' if nl == 'NO' else ''}")
    # constraints from pg_catalog: information_schema hides them from a SELECT-only role
    cur.execute("""select pg_get_constraintdef(oid) from pg_constraint where conrelid = %s::regclass and contype in ('p','f')
                   order by contype desc, conname""", (f"public.{t}",))
    cols += [f"    {d}" for (d,) in cur.fetchall()]
    out.append(f"CREATE TABLE {t} (\n" + ",\n".join(cols) + "\n);")
p = pathlib.Path(__file__).parent / "training" / "ddl.sql"; p.write_text("\n\n".join(out) + "\n"); print(f"wrote {p} ({len(out)} tables)")
