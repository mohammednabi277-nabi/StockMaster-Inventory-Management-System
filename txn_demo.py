import sqlite3, shutil, os, json, subprocess, sys, textwrap
SRC="stockmaster.db"; DB="txn_demo.db"
shutil.copy(SRC, DB)
log=[]
def say(s=""): print(s); log.append(s)
def conn(timeout=0.3):
    c=sqlite3.connect(DB, timeout=timeout, isolation_level=None)   # manual BEGIN/COMMIT
    c.execute("PRAGMA foreign_keys=ON"); return c
def qty(c,p,w): return c.execute("SELECT quantity FROM stock WHERE product_id=? AND warehouse_id=?",(p,w)).fetchone()[0]

def transfer(c, p, src, dst, n, simulate_fail=False, use_savepoint=True):
    c.execute("BEGIN IMMEDIATE")
    try:
        have = qty(c,p,src)                                   # 1. check source stock
        if have < n:
            c.execute("ROLLBACK"); return "ROLLED BACK (insufficient stock: have %d, need %d)"%(have,n)
        c.execute("UPDATE stock SET quantity=quantity-?, last_updated=date('now') WHERE product_id=? AND warehouse_id=?",(n,p,src))   # 2. deduct
        if use_savepoint: c.execute("SAVEPOINT after_deduct")
        if simulate_fail: raise RuntimeError("simulated crash while crediting destination")
        c.execute("UPDATE stock SET quantity=quantity+?, last_updated=date('now') WHERE product_id=? AND warehouse_id=?",(n,p,dst))   # 3. add
        c.execute("INSERT INTO stock_transfer_log(product_id,from_wh,to_wh,quantity) VALUES (?,?,?,?)",(p,src,dst,n))                   # 4. log
        c.execute("COMMIT"); return "COMMITTED"
    except Exception as e:
        c.execute("ROLLBACK"); return "ROLLED BACK (%s)"%e

a=conn()
P,S,D = 1,1,2     # Laptop Pro 15 : Dallas -> Houston
say("== 1. Stock Transfer: COMMIT ==")
say("Before : source(WH1)=%d  dest(WH2)=%d"%(qty(a,P,S),qty(a,P,D)))
say("Result : "+transfer(a,P,S,D,10))
say("After  : source(WH1)=%d  dest(WH2)=%d"%(qty(a,P,S),qty(a,P,D)))
say("Log    : "+str(a.execute("SELECT log_id,product_id,from_wh,to_wh,quantity FROM stock_transfer_log ORDER BY log_id DESC LIMIT 1").fetchone()))

say("\n== 2. Insufficient stock -> ROLLBACK ==")
say("Result : "+transfer(a,P,S,D,100000))
say("Stock unchanged: source(WH1)=%d"%qty(a,P,S))

say("\n== 3. SAVEPOINT / ROLLBACK TO ==")
a.execute("BEGIN")
a.execute("UPDATE stock SET quantity=quantity-5 WHERE product_id=? AND warehouse_id=?",(P,S))
say("After step-1 deduct (uncommitted): WH1=%d"%qty(a,P,S))
a.execute("SAVEPOINT sp1")
a.execute("UPDATE stock SET quantity=quantity+5 WHERE product_id=? AND warehouse_id=?",(P,D))
say("After step-2 credit (savepoint sp1 taken before): WH2=%d"%qty(a,P,D))
a.execute("ROLLBACK TO sp1")
say("ROLLBACK TO sp1 -> WH2 back to %d, WH1 still %d"%(qty(a,P,D),qty(a,P,S)))
a.execute("ROLLBACK")
say("Full ROLLBACK -> WH1=%d  WH2=%d (original values)"%(qty(a,P,S),qty(a,P,D)))

say("\n== 4. Concurrency: two managers ship the LAST unit ==")
a.execute("UPDATE stock SET quantity=1 WHERE product_id=? AND warehouse_id=?",(P,S))
m1,m2=conn(),conn()
m1.execute("BEGIN IMMEDIATE")
say("Manager-1 BEGIN IMMEDIATE (acquires write lock); sees qty = %d"%qty(m1,P,S))
try:
    m2.execute("BEGIN IMMEDIATE"); say("Manager-2 got lock (unexpected)")
except sqlite3.OperationalError as e:
    say("Manager-2 BEGIN IMMEDIATE -> BLOCKED: '%s'"%e)
m1.execute("UPDATE stock SET quantity=quantity-1 WHERE product_id=? AND warehouse_id=? AND quantity>=1",(P,S))
m1.execute("COMMIT"); say("Manager-1 ships the unit and COMMITs. qty now = %d"%qty(a,P,S))
say("Manager-2 retries: "+transfer(m2,P,S,D,1))
m1.close(); m2.close()

say("\n== 5. Deadlock-prone pattern: two sessions read, then both try to write ==")
s1,s2=conn(),conn()
s1.execute("BEGIN"); s2.execute("BEGIN")
s1.execute("SELECT COUNT(*) FROM stock").fetchone(); s2.execute("SELECT COUNT(*) FROM stock").fetchone()
say("S1 and S2 both BEGIN and read stock -> each holds a SHARED lock.")
s1.execute("UPDATE stock SET quantity=quantity WHERE product_id=1 AND warehouse_id=1")
say("S1 UPDATE succeeds -> S1 now holds the RESERVED (write-intent) lock; its COMMIT will need EXCLUSIVE, i.e. must wait for S2's SHARED lock.")
try:
    s2.execute("UPDATE stock SET quantity=quantity WHERE product_id=1 AND warehouse_id=2")
    say("S2 UPDATE succeeded")
except sqlite3.OperationalError as e:
    say("S2 UPDATE -> '%s'. S1 waits for S2 and S2 waits for S1 = circular wait; SQLite breaks it by failing S2 immediately with SQLITE_BUSY."%e)
s2.execute("ROLLBACK"); say("Resolution: victim S2 issues ROLLBACK (releases its SHARED lock).")
s1.execute("COMMIT"); say("S1 COMMIT now succeeds.")
s1.close(); s2.close()

say("\n== 6. Failure & recovery (crash mid-transfer, uncommitted work discarded) ==")
a.execute("UPDATE stock SET quantity=20 WHERE product_id=1 AND warehouse_id=1")   # restock WH1 so the transfer is valid
b=conn()
before=(qty(b,P,S),qty(b,P,D)); n_log=b.execute("SELECT COUNT(*) FROM stock_transfer_log").fetchone()[0]
say("Before crash: WH1=%d WH2=%d, log rows=%d"%(before+(n_log,)))
code = r'''
import sqlite3,os
c=sqlite3.connect("txn_demo.db",isolation_level=None)
c.execute("BEGIN IMMEDIATE")
c.execute("UPDATE stock SET quantity=quantity-7 WHERE product_id=1 AND warehouse_id=1")
print("child: deducted 7 units, uncommitted; WH1 inside txn =",c.execute("SELECT quantity FROM stock WHERE product_id=1 AND warehouse_id=1").fetchone()[0],flush=True)
os._exit(3)   # process killed before the destination credit / COMMIT
'''
r=subprocess.run([sys.executable,"-c",code],capture_output=True,text=True); rc=r.returncode; say(r.stdout.strip())
say("Process terminated abnormally (exit code %d) after deducting 7 units, before COMMIT."%rc)
say("Rollback-journal file left on disk (hot journal): %s"%os.path.exists(DB+"-journal"))
b2=conn()
after=(qty(b2,P,S),qty(b2,P,D)); n_log2=b2.execute("SELECT COUNT(*) FROM stock_transfer_log").fetchone()[0]
say("After restart (automatic rollback from journal): WH1=%d WH2=%d, log rows=%d"%(after+(n_log2,)))
say("Integrity check: "+b2.execute("PRAGMA integrity_check").fetchone()[0])
say("Recovered state identical to last committed state: %s"%(before+(n_log,)==after+(n_log2,)))
open("txn_output.txt","w").write("\n".join(log))
