"""Shared helpers: config, DB access, Cube JWT, result-set comparison."""
import base64, datetime as dt, decimal, hashlib, hmac, json, math, pathlib, re, time
from collections import Counter
from itertools import permutations
from dotenv import dotenv_values

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_env():
    import os
    env = {**dotenv_values(ROOT / ".env.example"), **dotenv_values(ROOT / ".env")}
    for k in list(env):  # real environment wins (e.g. OPENAI_API_KEY exported in shell)
        if os.environ.get(k):
            env[k] = os.environ[k]
    for k in ("OPENAI_API_KEY",):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def cube_token(secret, ttl=3600):
    b = lambda d: base64.urlsafe_b64encode(json.dumps(d, separators=(",", ":")).encode()).rstrip(b"=")
    now = int(time.time())
    msg = b({"alg": "HS256", "typ": "JWT"}) + b"." + b({"iat": now, "exp": now + ttl})
    sig = base64.urlsafe_b64encode(hmac.new(secret.encode(), msg, hashlib.sha256).digest()).rstrip(b"=")
    return (msg + b"." + sig).decode()


# ---------------- comparison ----------------
_NUM = re.compile(r"^-?\d+(\.\d+)?([eE][-+]?\d+)?$")
_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:[T ]00:00:00(?:\.0+)?(?:Z|\+00:00)?)?$")
_TS = re.compile(r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(?:\.\d+)?(?:Z|\+00:00)?$")


def norm(v):
    """Canonicalise one cell so equivalent values from Postgres / JSON APIs compare equal."""
    if v is None:
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float, decimal.Decimal)):
        f = float(v)
        if math.isnan(f):
            return None
        return round(f, 2) + 0.0
    if isinstance(v, dt.datetime):
        return v.date().isoformat() if v.time() == dt.time(0) else v.replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")
    if isinstance(v, dt.date):
        return v.isoformat()
    s = str(v).strip()
    if _NUM.match(s):
        return round(float(s), 2) + 0.0
    m = _DATE.match(s)
    if m:
        return m.group(1)
    m = _TS.match(s)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return s


def _year_coerce(gcol, pcol):
    """Gold column of integer years vs predicted column of YYYY-01-01 dates (Cube year granularity)."""
    if gcol and all(isinstance(g, float) and g.is_integer() and 1900 <= g <= 2100 for g in gcol if g is not None):
        if pcol and all(isinstance(p, str) and re.match(r"^\d{4}-01-01$", p) for p in pcol if p is not None):
            return [None if p is None else float(p[:4]) for p in pcol]
    return None


def _key(x):
    return (0, "") if x is None else ((1, x) if isinstance(x, float) else (2, str(x)))


def compare(gold_rows, pred_rows, order_matters=False, order_cols=None):
    """Execution-accuracy comparison.

    exact   : same #columns; some column permutation makes the row multisets equal.
    relaxed : prediction may have EXTRA columns; gold columns must map onto distinct pred columns.
    Row order is only checked when order_matters (on gold columns `order_cols`, so ties don't matter).
    Returns dict(exact=bool, relaxed=bool, reason=str).
    """
    G = [[norm(v) for v in r] for r in gold_rows]
    P = [[norm(v) for v in r] for r in pred_rows]
    if len(G) != len(P):
        return {"exact": False, "relaxed": False, "reason": f"row count {len(P)} != gold {len(G)}"}
    if not G:
        return {"exact": True, "relaxed": True, "reason": "both empty"}
    ng, npd = len(G[0]), len(P[0])
    gcols = [[r[i] for r in G] for i in range(ng)]
    pcols = [[r[j] for r in P] for j in range(npd)]
    # candidate pred columns per gold column (column-value multisets equal)
    cands = []
    for i in range(ng):
        gs = sorted(gcols[i], key=_key)
        c = []
        for j in range(npd):
            pc = pcols[j]
            if sorted(pc, key=_key) == gs:
                c.append((j, None))
            else:
                yc = _year_coerce(gcols[i], pc)
                if yc is not None and sorted(yc, key=_key) == gs:
                    c.append((j, yc))
        if not c:
            return {"exact": False, "relaxed": False, "reason": f"no predicted column matches gold column {i}"}
        cands.append(c)

    gold_ms = Counter(tuple(r) for r in G)
    found = None

    def search(i, used, chosen):
        nonlocal found
        if found:
            return
        if i == ng:
            proj = [tuple((chosen[k][1][r] if chosen[k][1] is not None else pcols[chosen[k][0]][r]) for k in range(ng)) for r in range(len(P))]
            if Counter(proj) == gold_ms:
                if order_matters:
                    oc = order_cols if order_cols is not None else list(range(ng))
                    if [tuple(p[c] for c in oc) for p in proj] != [tuple(g[c] for c in oc) for g in G]:
                        return
                found = list(chosen)
            return
        for j, yc in cands[i]:
            if j not in used:
                search(i + 1, used | {j}, chosen + [(j, yc)])

    search(0, frozenset(), [])
    if not found:
        why = "rows differ" + (" or order differs" if order_matters else "")
        return {"exact": False, "relaxed": False, "reason": why}
    exact = npd == ng
    return {"exact": exact, "relaxed": True, "reason": "match" if exact else f"match with {npd - ng} extra column(s)"}
