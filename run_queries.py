import sqlite3, re, json, sys
con = sqlite3.connect("stockmaster.db"); con.execute("PRAGMA foreign_keys=ON")
txt = open("queries.sql").read()
blocks = re.split(r"^-- @", txt, flags=re.M)[1:]
con.execute("DROP VIEW IF EXISTS v_product_global_stock")
out = []
res = {}
for b in blocks:
    head, _, body = b.partition("\n")
    qid, title = [x.strip() for x in head.split("|",1)]
    sql = "\n".join(l for l in body.splitlines() if not l.startswith("-- =====")).strip()
    cur = con.execute(sql)
    if sql.upper().startswith("CREATE"):
        out.append(dict(id=qid,title=title,sql=sql,cols=[],rows=[],total=0)); continue
    cols=[d[0] for d in cur.description]; rows=cur.fetchall()
    res[qid]=rows
    out.append(dict(id=qid,title=title,sql=sql,cols=cols,rows=rows[:10],total=len(rows)))
for a,b in [("Q7a","Q7b"),("Q8a","Q8b"),("Q10a","Q10b"),("Q17a","Q17b")]:
    print(a,b,"identical:",sorted(res[a])==sorted(res[b]), len(res[a]))
json.dump(out, open("query_results.json","w"), default=str, indent=1)
for o in out:
    print("\n###",o["id"],o["title"],"(%d rows)"%o["total"]); print(o["cols"])
    for r in o["rows"][:6]: print(r)
