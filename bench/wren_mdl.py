"""Build the WrenAI semantic layer (MDL) on the SECOND Wren stack (wrenai_mdl, port 3001):
1. connect data source + tables + PK/FK (same code path as the out-of-the-box stack)
2. model/column display names + descriptions, relationship descriptions   (updateModelMetadata)
3. calculated fields                                                       (createCalculatedField)
4. global instructions                                                     (createInstruction)
5. deploy and require status SUCCESS; dump the deployed MDL to wrenai_mdl/mdl/deployed_mdl.json
Idempotent: re-running skips calculated fields / instructions that already exist.
Usage: python bench/wren_mdl.py [--force]   (--force re-onboards the project from scratch)
       python bench/wren_mdl.py --redeploy  (after wren-ai-service was recreated, e.g. a variant switch: its qdrant
       collections are recreated at start (recreate_index: true), so re-deploy the unchanged project and re-index the
       existing instructions; verifies the MDL hash equals wrenai_mdl/mdl/deployed_mdl.json and the index counts)"""
import argparse, json, sys, time
import httpx, yaml
import setup_connections as sc
from common import ROOT

env = sc.env
URL = f"http://localhost:{env.get('WREN_MDL_UI_PORT', '3001')}"
SPEC = yaml.safe_load(open(ROOT / "wrenai_mdl" / "mdl" / "semantic_layer.yaml"))


def g(c, q, v=None):
    return sc.gql(c, q, v, wren=URL)


def diagram(c):
    return g(c, """{ diagram { models { modelId referenceName sourceTableName
        fields { columnId referenceName }
        calculatedFields { columnId referenceName }
        relationFields { relationId fromModelName fromColumnName toModelName toColumnName } } } }""")["diagram"]["models"]


def qdrant_counts():
    import subprocess
    out = {}
    for col in ("table_descriptions", "Document", "instructions", "sql_pairs", "view_questions"):
        r = subprocess.run(["docker", "exec", "wrenai-mdl-wren-ai-service-1", "python", "-c",
                            f"import urllib.request,json;print(json.load(urllib.request.urlopen('http://qdrant:6333/collections/{col}'))['result']['points_count'])"],
                           capture_output=True, text=True)
        out[col] = int(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip().isdigit() else None
    return out


def redeploy():
    with httpx.Client(timeout=300) as c:
        d = g(c, "mutation{ deploy(force:true) }")["deploy"]
        if d.get("status") != "SUCCESS":
            sys.exit(f"[mdl] DEPLOY FAILED {d}")
        ins = g(c, "{ instructions { id instruction questions isDefault } }")["instructions"]
        for i in ins:  # no-op update -> wren-ui re-sends the instruction to wren-ai-service for indexing
            g(c, "mutation($w: InstructionWhereInput!, $d: UpdateInstructionInput!){ updateInstruction(where:$w, data:$d){ id } }",
              {"w": {"id": i["id"]}, "d": {"instruction": i["instruction"], "questions": i["questions"], "isDefault": i["isDefault"]}})
    want = json.loads((ROOT / "wrenai_mdl" / "mdl" / "deployed_mdl.json").read_text())["hash"]
    got = httpx.get(f"{URL}/api/v1/models", timeout=60).json()["hash"]
    counts = qdrant_counts()
    print(f"[mdl] redeployed; MDL hash {got} ({'== deployed_mdl.json' if got == want else 'DIFFERS from ' + want}); "
          f"instructions re-indexed {len(ins)}; qdrant {counts}")
    if got != want or counts.get("instructions") != len(SPEC["instructions"]) or counts.get("sql_pairs") != 0:
        sys.exit("[mdl] redeploy verification FAILED")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--force", action="store_true")
    ap.add_argument("--redeploy", action="store_true"); a = ap.parse_args()
    if a.redeploy:
        return redeploy()
    # 1. data source: the second stack reaches Postgres via the host's published port
    sc.WREN = URL
    sc.PG = {**sc.PG, "host": "host.docker.internal", "port": int(env.get("PG_HOST_PORT", "5432"))}
    with httpx.Client(timeout=300) as c:
        st = g(c, "{ onboardingStatus { status } }")["onboardingStatus"]["status"]
        if st != "ONBOARDING_FINISHED" or a.force:
            g(c, "mutation($d: DataSourceInput!){ saveDataSource(data:$d){ type } }",
              {"d": {"type": "POSTGRES", "properties": {"displayName": "chinook-semantic", **sc.PG, "ssl": False}}})
            tables = [t["name"] for t in g(c, "{ listDataSourceTables { name } }")["listDataSourceTables"]]
            g(c, "mutation($d: SaveTablesInput!){ saveTables(data:$d) }", {"d": {"tables": tables}})
            orig, sc.gql = sc.gql, (lambda c2, q, v=None, wren=None: orig(c2, q, v, wren=URL))
            try:
                n_pk, n_rel = sc.wren_keys_and_relations(c)
            finally:
                sc.gql = orig
            print(f"[mdl] onboarded {len(tables)} tables, {n_pk} PKs, {n_rel} relationships")
        else:
            print("[mdl] project already onboarded")

        models = diagram(c)
        by_tbl = {m["sourceTableName"].split(".")[-1]: m for m in models}
        col_id = lambda t, col: next(f["columnId"] for f in by_tbl[t]["fields"] if f["referenceName"] == col)
        ref2tbl = {m["referenceName"]: t for t, m in by_tbl.items()}

        def rel_id(spec):  # "a.col->b.col"
            (ft, fc), (tt, tc) = [x.split(".") for x in spec.split("->")]
            for m in models:
                for r in m["relationFields"]:
                    if (ref2tbl.get(r["fromModelName"]), r["fromColumnName"], ref2tbl.get(r["toModelName"]), r["toColumnName"]) == (ft, fc, tt, tc):
                        return r["relationId"]
            raise KeyError(spec)

        # 2. metadata
        rel_desc = {rel_id(k): v for k, v in SPEC["relationships"].items()}
        for t, ms in SPEC["models"].items():
            m = by_tbl[t]
            rels = [{"id": rid, "description": d} for rid, d in rel_desc.items()
                    if any(r["relationId"] == rid for r in m["relationFields"])]
            g(c, "mutation($w: ModelWhereInput!, $d: UpdateModelMetadataInput!){ updateModelMetadata(where:$w, data:$d) }",
              {"w": {"id": m["modelId"]}, "d": {
                  "displayName": ms["display_name"], "description": ms["description"],
                  "columns": [{"id": col_id(t, cn), "displayName": cv["display_name"], "description": cv["description"]}
                              for cn, cv in ms["columns"].items()],
                  "relationships": rels}})
        print(f"[mdl] metadata: {len(SPEC['models'])} models, "
              f"{sum(len(m['columns']) for m in SPEC['models'].values())} columns, {len(rel_desc)} relationship descriptions")

        # 3. calculated fields
        made = 0
        for cf in SPEC["calculated_fields"]:
            m = by_tbl[cf["model"]]
            if any(x["referenceName"] == cf["name"] for x in m["calculatedFields"]):
                continue
            ct, cc = cf["column"].split(".")
            lineage = [rel_id(p) for p in cf["path"]] + [col_id(ct, cc)]
            g(c, "mutation($d: CreateCalculatedFieldInput!){ createCalculatedField(data:$d) }",
              {"d": {"modelId": m["modelId"], "name": cf["name"], "expression": cf["expression"], "lineage": lineage}})
            made += 1
        models = diagram(c); by_tbl = {m["sourceTableName"].split(".")[-1]: m for m in models}
        for cf in SPEC["calculated_fields"]:  # descriptions for calculated fields
            m = by_tbl[cf["model"]]
            fid = next(x["columnId"] for x in m["calculatedFields"] if x["referenceName"] == cf["name"])
            g(c, "mutation($w: ModelWhereInput!, $d: UpdateModelMetadataInput!){ updateModelMetadata(where:$w, data:$d) }",
              {"w": {"id": m["modelId"]}, "d": {"calculatedFields": [{"id": fid, "description": cf["description"]}]}})
        print(f"[mdl] calculated fields: {made} created, {len(SPEC['calculated_fields'])} defined")

        # 4. instructions
        have = {i["instruction"] for i in g(c, "{ instructions { id instruction } }")["instructions"]}
        new = [i for i in SPEC["instructions"] if i not in have]
        for i in new:
            g(c, "mutation($d: CreateInstructionInput!){ createInstruction(data:$d){ id } }",
              {"d": {"instruction": i, "questions": [], "isDefault": True}})
        print(f"[mdl] instructions: {len(new)} created, {len(SPEC['instructions'])} defined; sql pairs: "
              f"{len(g(c, '{ sqlPairs { id } }')['sqlPairs'])}")

        # 5. deploy
        d = g(c, "mutation{ deploy(force:true) }")["deploy"]
        print(f"[mdl] deploy -> {json.dumps(d)[:300]}")
        if d.get("status") != "SUCCESS":
            sys.exit("[mdl] DEPLOY FAILED")
        mdl = httpx.get(f"{URL}/api/v1/models", timeout=60).json()
        (ROOT / "wrenai_mdl" / "mdl" / "deployed_mdl.json").write_text(json.dumps(mdl, indent=1, ensure_ascii=False))
        print(f"[mdl] deployed MDL hash {mdl.get('hash')} -> wrenai_mdl/mdl/deployed_mdl.json")


if __name__ == "__main__":
    main()
