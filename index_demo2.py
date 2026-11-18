import sqlite3, time, json, random
res = json.load(open("index_results.json"))
con = sqlite3.connect("stockmaster.db")
def plan(sql): return [r[3] for r in con.execute("EXPLAIN QUERY PLAN "+sql)]
def bench(sql,n=300):
    t=time.perf_counter()
    for _ in range(n): con.execute(sql).fetchall()
    return (time.perf_counter()-t)/n*1000

# Rewrite 2: Q15 naive (fan-out) vs pre-aggregated
naive = """SELECT p.product_name, SUM(soi.quantity) AS units_sold, SUM(st.quantity) AS stock
FROM product p
JOIN sales_order_item soi ON soi.product_id = p.product_id
JOIN sales_order so ON so.so_id = soi.so_id AND so.status='Shipped' AND so.order_date >= date('now','-12 months')
JOIN stock st ON st.product_id = p.product_id
GROUP BY p.product_id"""
opt = """SELECT p.product_name, sold.units_sold, stk.total_stock
FROM product p
JOIN (SELECT soi.product_id, SUM(soi.quantity) AS units_sold FROM sales_order_item soi
      JOIN sales_order so ON so.so_id=soi.so_id AND so.status='Shipped' AND so.order_date >= date('now','-12 months')
      GROUP BY soi.product_id) sold ON sold.product_id = p.product_id
JOIN (SELECT product_id, SUM(quantity) AS total_stock FROM stock GROUP BY product_id) stk ON stk.product_id = p.product_id"""
rn = con.execute(naive).fetchall(); ro = con.execute(opt).fetchall()
# naive units_sold is multiplied by number of warehouse rows
chk = {r[0]:r[1] for r in ro}; inflated = sum(1 for r in rn if r[1]!=chk[r[0]])
res["o3"] = dict(id="O3",title="Q15 stock turnover (fan-out fix)",orig=naive,opt=opt,
   plan_orig=plan(naive),t_orig=round(bench(naive),4),plan_opt=plan(opt),t_opt=round(bench(opt),4),
   rows_naive=len(rn),rows_opt=len(ro),inflated_rows=inflated)

# scale-up benchmark: 300k stock rows
random.seed(1)
con.execute("DROP TABLE IF EXISTS stock_big")
con.execute("CREATE TABLE stock_big(product_id INT, warehouse_id INT, quantity INT)")
con.executemany("INSERT INTO stock_big VALUES (?,?,?)",[(p,w,random.randint(0,500)) for p in range(1,7501) for w in range(1,41)])
q="SELECT product_id, quantity FROM stock_big WHERE warehouse_id = 17 AND quantity < 5"
b_plan,b_t=plan(q),bench(q,100)
con.execute("CREATE INDEX idx_big_wh ON stock_big(warehouse_id, quantity)")
a_plan,a_t=plan(q),bench(q,100)
res["scale"]=dict(rows=300000,sql=q,before=b_plan,after=a_plan,t_before=round(b_t,3),t_after=round(a_t,3))
con.execute("DROP TABLE stock_big"); con.commit()
json.dump(res,open("index_results.json","w"),indent=1)
print(json.dumps({k:res[k] for k in ("o3","scale")},indent=1))
