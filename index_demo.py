import sqlite3, time, json
con = sqlite3.connect("stockmaster.db"); con.execute("PRAGMA foreign_keys=ON")
for ix in ["idx_product_sku","idx_stock_warehouse","idx_ps_supplier","idx_po_supplier_status","idx_return_product","idx_soi_product"]:
    con.execute("DROP INDEX IF EXISTS "+ix)
con.execute("DROP TABLE IF EXISTS product_noidx")
con.execute("CREATE TABLE product_noidx AS SELECT * FROM product")   # CTAS copy: no PK/UNIQUE => no implicit index

def plan(sql):
    return [r[3] for r in con.execute("EXPLAIN QUERY PLAN "+sql)]
def bench(sql, n=3000):
    t=time.perf_counter()
    for _ in range(n): con.execute(sql).fetchall()
    return (time.perf_counter()-t)/n*1000

tests = [
 ("A","Lookup product by SKU",
  "SELECT * FROM product_noidx WHERE product_sku = 'ELE-1007'",
  "SELECT * FROM product WHERE product_sku = 'ELE-1007'","idx_product_sku"),
 ("B","Stock for one warehouse (warehouse_id)",
  "SELECT p.product_name, s.quantity FROM stock s JOIN product p ON p.product_id=s.product_id WHERE s.warehouse_id = 3",
  None,"idx_stock_warehouse"),
 ("C","Products of one supplier (supplier_id)",
  "SELECT p.product_name FROM product_supplier ps JOIN product p ON p.product_id=ps.product_id WHERE ps.supplier_id = 1",
  None,"idx_ps_supplier"),
]
res=[]
# Product SKU: before = table without index, after = indexed table
for tid,title,before,after,ix in tests:
    if after is None: after=before
    if tid=="A":
        b_plan,b_t = plan(before), bench(before)
        con.execute("CREATE INDEX idx_product_sku ON product(product_sku)")
        a_plan,a_t = plan(after), bench(after)
    else:
        b_plan,b_t = plan(before), bench(before)
        col = {"idx_stock_warehouse":"stock(warehouse_id)","idx_ps_supplier":"product_supplier(supplier_id)"}[ix]
        con.execute("CREATE INDEX %s ON %s"%(ix,col))
        a_plan,a_t = plan(after), bench(after)
    res.append(dict(id=tid,title=title,sql=after,before=b_plan,after=a_plan,t_before=round(b_t,4),t_after=round(a_t,4)))

# Optimisation 1: Q10a  suppliers with no delivery in last 3 months
q10_orig = """SELECT s.supplier_id, s.supplier_name FROM supplier s
WHERE NOT EXISTS (SELECT 1 FROM purchase_order po WHERE po.supplier_id = s.supplier_id
 AND po.status='Delivered' AND po.delivered_date >= date('now','-3 months'))"""
q10_opt = """SELECT s.supplier_id, s.supplier_name FROM supplier s
WHERE s.supplier_id NOT IN (SELECT DISTINCT supplier_id FROM purchase_order
 WHERE status='Delivered' AND delivered_date >= date('now','-3 months'))"""
b_plan,b_t = plan(q10_orig), bench(q10_orig)        # before composite index
con.execute("CREATE INDEX idx_po_supplier_status ON purchase_order(supplier_id, status, delivered_date)")
a_plan0, a_t0 = plan(q10_orig), bench(q10_orig)
a_plan, a_t = plan(q10_opt), bench(q10_opt)
r10 = dict(id="O1",title="Q10 suppliers with no delivery in 3 months",orig=q10_orig,opt=q10_opt,
  plan_orig_noidx=b_plan,t_orig_noidx=round(b_t,4),plan_orig_idx=a_plan0,t_orig_idx=round(a_t0,4),plan_opt=a_plan,t_opt=round(a_t,4),
  same = sorted(con.execute(q10_orig).fetchall())==sorted(con.execute(q10_opt).fetchall()))

# Optimisation 2: Q19 returns > 10 : aggregate first, join later
q19_orig = """SELECT p.product_name, COUNT(*) AS return_count, SUM(r.quantity) AS units_returned
FROM sales_return r JOIN product p ON p.product_id = r.product_id
GROUP BY p.product_id HAVING COUNT(*) > 10 ORDER BY return_count DESC"""
q19_opt = """SELECT p.product_name, x.return_count, x.units_returned
FROM (SELECT product_id, COUNT(*) AS return_count, SUM(quantity) AS units_returned
      FROM sales_return GROUP BY product_id HAVING COUNT(*) > 10) x
JOIN product p ON p.product_id = x.product_id ORDER BY x.return_count DESC"""
b_plan,b_t = plan(q19_orig), bench(q19_orig)
con.execute("CREATE INDEX idx_return_product ON sales_return(product_id, quantity)")
a_plan, a_t = plan(q19_opt), bench(q19_opt)
r19 = dict(id="O2",title="Q19 items returned more than 10 times",orig=q19_orig,opt=q19_opt,
  plan_orig=b_plan,t_orig=round(b_t,4),plan_opt=a_plan,t_opt=round(a_t,4),
  same = sorted(con.execute(q19_orig).fetchall())==sorted(con.execute(q19_opt).fetchall()))
con.execute("CREATE INDEX idx_soi_product ON sales_order_item(product_id)")
con.execute("DROP TABLE product_noidx")
con.commit()
json.dump(dict(tests=res,o1=r10,o2=r19), open("index_results.json","w"), indent=1)
print(json.dumps(dict(tests=res,o1=r10,o2=r19), indent=1))
print([r[1] for r in con.execute("SELECT * FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")])
