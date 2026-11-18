import sqlite3, random, os
from datetime import date, timedelta
random.seed(2026)
TODAY = date.today()
DB = "stockmaster.db"
if os.path.exists(DB): os.remove(DB)
con = sqlite3.connect(DB)
con.executescript(open("schema.sql").read())
c = con.cursor()
d = lambda x: x.isoformat()

cats = ["Electronics", "Furniture", "Appliances", "Office Supplies"]
c.executemany("INSERT INTO category VALUES (?,?)", list(enumerate(cats, 1)))

suppliers = [("TechGlobal","Austin"),("Pacific Components","San Jose"),("Lone Star Electronics","Dallas"),
 ("NorthWind Furnishings","Chicago"),("HomeCraft Supply","Atlanta"),("Summit Office Depot","Denver"),
 ("BrightLine Appliances","Columbus"),("Metro Tech Wholesale","New York"),("Evergreen Furniture","Seattle"),
 ("Sunbelt Distributors","Phoenix")]
for i,(n,city) in enumerate(suppliers,1):
    c.execute("INSERT INTO supplier VALUES (?,?,?,?,?)",
      (i,n,n.lower().replace(" ","")+"@supply.com","555-01%02d"%i,city))

# (name, category, price, volume cu.ft, reorder_point)
P = []
for i,(m,p) in enumerate([("Laptop Pro 15",1450),("Laptop Air 13",980),("Laptop Gaming X",1899),
        ("Laptop Business 14",1120),("Laptop Student 11",449),("Laptop Ultra 16",2150)]): P.append((m,1,p,2.2,25))
for m,p in [("Smartphone Nova 5G",799),("Smartphone Lite",299),("Smartphone Max",1099),
            ("Smartphone Edge",649),("Smartphone Basic",149),("Smartphone Fold",1699)]: P.append((m,1,p,0.4,60))
for m,p in [("Tablet Slate 10",429),("Tablet Mini 8",329),("Tablet Pro 12",899),("Tablet Kids 7",129)]: P.append((m,1,p,0.9,30))
for m,p in [("Monitor 24 inch",189),("Monitor 27 inch 4K",459),("Monitor Ultrawide 34",649),("Monitor Portable 15",219)]: P.append((m,1,p,4.0,20))
for m,p in [("Headphones Wireless",129),("Headphones Studio",249),("Earbuds Pro",179)]: P.append((m,1,p,0.3,50))
for m,p in [("Smart TV 43 inch",379),("Smart TV 55 inch",599),("Smart TV 65 inch",849)]: P.append((m,1,p,12.0,15))
for m,p in [("WiFi Router AX",119),("Mesh WiFi System",249)]: P.append((m,1,p,1.0,30))
for m,p in [("Office Desk Oak",329),("Standing Desk Electric",599),("Ergonomic Chair",279),("Executive Chair Leather",449),
            ("Bookshelf 5-Tier",149),("Filing Cabinet 4-Drawer",189),("Conference Table 8-Seat",899),
            ("Sofa 3-Seater",749),("Coffee Table Glass",159),("Bed Frame Queen",519),("Wardrobe 3-Door",429),
            ("Dining Table 6-Seat",569)]: P.append((m,2,p,[18,22,14,16,12,10,40,45,9,35,30,28][len([x for x in P if x[1]==2])],12))
for m,p,v in [("Microwave Oven",129,2.5),("Refrigerator 18 cu ft",899,32),("Washing Machine",649,18),("Air Fryer",99,1.5),
              ("Vacuum Cleaner Robot",349,1.8),("Dishwasher",579,16),("Electric Kettle",39,0.6),("Air Purifier",189,3)]:
    P.append((m,3,p,v,18))
for m,p,v in [("Printer Laser",229,3.5),("Paper Ream A4 (Box 5)",34,1.2),("Ink Cartridge Set",59,0.2),("Stapler Heavy Duty",19,0.15),
              ("Whiteboard 4x3",89,2.5),("Desk Organizer",24,0.5),("Shredder",139,2.8),("Label Maker",49,0.3)]:
    P.append((m,4,p,v,70))
SKU = {1:"ELE",2:"FUR",3:"APP",4:"OFF"}
for i,(n,ct,p,v,rp) in enumerate(P,1):
    c.execute("INSERT INTO product VALUES (?,?,?,?,?,?,?)",(i,"%s-%04d"%(SKU[ct],1000+i),n,ct,p,v,rp))
NP = len(P)

# supplier <-> product (category affinity; TechGlobal supplies electronics heavily)
aff = {1:[1,2,3,8,10],2:[4,9,5],3:[7,5],4:[6,10]}
ps=set()
for pid,(n,ct,*_) in enumerate(P,1):
    cnt = random.choice([1,2,2,3])
    chosen = random.sample(aff[ct], min(cnt,len(aff[ct])))
    if ct==1 and pid%2==0 and 1 not in chosen: chosen.append(1)
    for s in chosen: ps.add((pid,s))
c.executemany("INSERT INTO product_supplier VALUES (?,?)", sorted(ps))

# warehouses
W = [("Dallas Central DC","Dallas","Texas"),("Houston Gulf DC","Houston","Texas"),("Austin Tech Hub","Austin","Texas"),
     ("Los Angeles West DC","Los Angeles","California"),("Chicago Midwest DC","Chicago","Illinois"),
     ("Newark East DC","Newark","New Jersey"),("Atlanta South DC","Atlanta","Georgia"),("Seattle North DC","Seattle","Washington")]
for i,(n,city,st) in enumerate(W,1): c.execute("INSERT INTO warehouse VALUES (?,?,?,?,100)",(i,n,city,st))

# stock
zero_all = {4, 12, 14, 17}              # products with no stock anywhere
partial  = {p: random.sample(range(1,9), random.randint(3,7)) for p in random.sample(range(1,NP+1), 22)}
rows=[]
for pid in range(1,NP+1):
    rp = P[pid-1][4]
    for w in range(1,9):
        if pid in partial and w not in partial[pid]: continue
        if pid in zero_all: q=0
        else:
            r=random.random()
            if r<0.10: q=0
            elif r<0.30: q=random.randint(1,max(1,rp-1))          # below reorder point
            else: q=random.randint(rp, rp*5)
        upd = TODAY - timedelta(days=random.randint(0,60))
        rows.append([pid,w,q,upd])
for r in random.sample(rows,14): r[3]=TODAY        # entries updated today
c.executemany("INSERT INTO stock VALUES (?,?,?,?)",[(a,b,q,d(u)) for a,b,q,u in rows])
# calibrate capacity so utilisation varies (two warehouses > 90 %)
targets=[0.93,0.72,0.55,0.91,0.64,0.80,0.47,0.88]
for w,t in enumerate(targets,1):
    used = c.execute("SELECT SUM(s.quantity*p.unit_volume) FROM stock s JOIN product p USING(product_id) WHERE warehouse_id=?",(w,)).fetchone()[0]
    c.execute("UPDATE warehouse SET capacity=? WHERE warehouse_id=?",(round(used/t,2),w))

# customers
first=["Olivia","Liam","Emma","Noah","Ava","Ethan","Sophia","Mason","Mia","Lucas","Isabella","Logan","Amelia","James","Harper","Elijah","Ella","Henry","Grace","Jack"]
last=["Smith","Johnson","Brown","Davis","Miller","Wilson","Moore","Taylor","Anderson","Thomas","Jackson","White","Harris","Martin","Clark"]
cities=["Dallas","Houston","Austin","Chicago","Seattle","Newark","Atlanta","Los Angeles","Denver","Miami"]
for i in range(1,41):
    n="%s %s"%(random.choice(first),random.choice(last))
    c.execute("INSERT INTO customer VALUES (?,?,?,?)",(i,n,"%s%d@mail.com"%(n.lower().replace(" ","."),i),random.choice(cities)))

# purchase orders (inbound): 14 months
lead = {1:5,2:9,3:4,4:11,5:7,6:6,7:8,8:5,9:12,10:10}     # mean lead days per supplier
sup_prods={}
for p,s in ps: sup_prods.setdefault(s,[]).append(p)
po_id=0
months_w = [1,1,1,2,1,1,2,2,3,1,1,2,3,4]    # extra weight for a peak month
start = TODAY - timedelta(days=420)
for k in range(130):
    s = random.choice(list(sup_prods))
    od = start + timedelta(days=random.randint(0,419))
    if od.month in (9,10) and random.random()<0.5: od = od.replace(day=min(od.day,28))
    lt = max(2, int(random.gauss(lead[s],2)))
    exp = od + timedelta(days=lead[s])
    dl = od + timedelta(days=lt)
    if s in (9,10) and dl >= TODAY - timedelta(days=95):            # inactive suppliers: nothing delivered recently
        od = TODAY - timedelta(days=random.randint(130,300)); exp = od+timedelta(days=lead[s]); dl = od+timedelta(days=lt)
    if dl > TODAY: status,dl_s='Ordered',None
    elif random.random()<0.04: status,dl_s='Cancelled',None
    else: status,dl_s='Delivered',d(dl)
    po_id+=1
    c.execute("INSERT INTO purchase_order VALUES (?,?,?,?,?,?,?)",(po_id,s,random.randint(1,8),d(od),d(exp),dl_s,status))
    for p in random.sample(sup_prods[s], min(len(sup_prods[s]), random.randint(1,3))):
        c.execute("INSERT INTO purchase_order_item VALUES (?,?,?,?)",(po_id,p,random.randint(20,200),round(P[p-1][2]*random.uniform(0.55,0.75),2)))

# sales orders (outbound): 12 months; dead-stock products not sold in last 6 months
dead = {5, 15, 21, 29, 33, 41, 49, 55}
hot  = [7, 9, 1, 3, 8, 13]                     # high-demand products
pool = [p for p in range(1,NP+1)]
so_items=[]
for so in range(1,361):
    od = TODAY - timedelta(days=random.randint(0,364))
    st = 'Shipped' if od < TODAY-timedelta(days=2) and random.random()>0.03 else ('Placed' if od>=TODAY-timedelta(days=2) else 'Cancelled')
    sd = d(od+timedelta(days=random.randint(1,3))) if st=='Shipped' else None
    if sd and sd>d(TODAY): sd=d(TODAY)
    c.execute("INSERT INTO sales_order VALUES (?,?,?,?,?,?)",(so,random.randint(1,40),random.randint(1,8),d(od),sd,st))
    n = random.randint(1,4)
    items=set()
    while len(items)<n:
        p = random.choice(hot) if random.random()<0.35 else random.choice(pool)
        if p in dead and od > TODAY-timedelta(days=185): continue
        items.add(p)
    for p in items:
        q = random.randint(1,6) if p in hot else random.randint(1,4)
        c.execute("INSERT INTO sales_order_item VALUES (?,?,?,?)",(so,p,q,P[p-1][2]))
        so_items.append((so,p,q,od))

# returns: concentrate on 3 problem products (>10 returns) + scattered others
by_prod={}
for so,p,q,od in so_items: by_prod.setdefault(p,[]).append((so,p,q,od))
rid=0; seen=set()
def add_ret(t):
    global rid
    so,p,q,od=t
    if (so,p) in seen: return
    seen.add((so,p)); rid+=1
    rd = min(TODAY, od+timedelta(days=random.randint(5,25)))
    c.execute("INSERT INTO sales_return VALUES (?,?,?,?,?,?)",(rid,so,p,random.randint(1,q),d(rd),random.choice(["Defective","Wrong item","Damaged in transit","Changed mind","Not as described"])))
for p in (7,9,1):
    for t in random.sample(by_prod[p], 13): add_ret(t)
for t in random.sample(so_items, 45): add_ret(t)

# transfer log history
for i in range(1,13):
    a,b = random.sample(range(1,9),2)
    c.execute("INSERT INTO stock_transfer_log VALUES (?,?,?,?,?,?,?)",
      (i,random.randint(1,NP),a,b,random.randint(5,40),d(TODAY-timedelta(days=random.randint(1,90)))+" 10:00:00","COMPLETED"))
con.commit()
for t in ["category","supplier","product","warehouse","product_supplier","stock","customer","purchase_order","purchase_order_item","sales_order","sales_order_item","sales_return","stock_transfer_log"]:
    print("%-22s %5d"%(t,c.execute("SELECT COUNT(*) FROM "+t).fetchone()[0]))
print("TOTAL", sum(c.execute("SELECT COUNT(*) FROM "+t).fetchone()[0] for t in ["category","supplier","product","warehouse","product_supplier","stock","customer","purchase_order","purchase_order_item","sales_order","sales_order_item","sales_return","stock_transfer_log"]))
