import sqlite3, shutil, hashlib
shutil.copy("stockmaster.db","sqli_demo.db")
con=sqlite3.connect("sqli_demo.db")
con.execute("CREATE TABLE app_user(user_id INTEGER PRIMARY KEY, username VARCHAR(30) UNIQUE NOT NULL, password_hash CHAR(64) NOT NULL, role VARCHAR(20) NOT NULL CHECK(role IN ('admin','manager','auditor','sales')))")
h=lambda s: hashlib.sha256(s.encode()).hexdigest()
con.executemany("INSERT INTO app_user VALUES (?,?,?,?)",[(1,"admin",h("Adm!n#2026"),"admin"),(2,"manager1",h("Mgr@Dallas9"),"manager"),(3,"auditor1",h("Aud1t0r!"),"auditor")])
con.commit()
out=[]
def say(s=""): print(s); out.append(s)

# ---------- VULNERABLE ----------
def login_vulnerable(user,pwd):
    sql="SELECT user_id, username, role FROM app_user WHERE username = '%s' AND password_hash = '%s'"%(user,h(pwd))
    say("  SQL sent : "+sql)
    return con.execute(sql).fetchall()
def search_vulnerable(term):
    sql="SELECT product_name, unit_price FROM product WHERE product_name LIKE '%%%s%%'"%term
    say("  SQL sent : "+sql)
    return con.execute(sql).fetchall()

# ---------- SECURE ----------
def login_secure(user,pwd):
    sql="SELECT user_id, username, role FROM app_user WHERE username = ? AND password_hash = ?"
    say("  SQL sent : "+sql+"   params=(%r, <sha256>)"%user)
    return con.execute(sql,(user,h(pwd))).fetchall()
def search_secure(term):
    if len(term)>50 or not all(ch.isalnum() or ch in " -_." for ch in term):
        say("  Input validation: rejected (illegal characters)"); return []
    sql="SELECT product_name, unit_price FROM product WHERE product_name LIKE ?"
    say("  SQL sent : "+sql+"   params=(%r,)"%('%'+term+'%'))
    return con.execute(sql,('%'+term+'%',)).fetchall()

say("=== ATTACK 1: authentication bypass (vulnerable login) ===")
say("Normal login  admin / wrongpassword:")
say("  Result   : %s"%login_vulnerable("admin","wrongpassword"))
say("Attacker input  username = admin' --   password = anything")
say("  Result   : %s   <-- logged in as admin WITHOUT the password"%login_vulnerable("admin' --","anything"))
say("\n=== ATTACK 1 against the SECURE version ===")
say("  Result   : %s   <-- attack treated as a literal username, login fails"%login_secure("admin' --","anything"))

say("\n=== ATTACK 2: UNION-based data theft (vulnerable product search) ===")
say("Normal search 'Laptop Pro':")
say("  Result   : %s"%search_vulnerable("Laptop Pro"))
payload="zzz' UNION SELECT username, password_hash FROM app_user --"
say("Attacker input: "+payload)
rows=search_vulnerable(payload)
for r in rows: say("  LEAKED   : %s"%(r,))
say("\n=== ATTACK 2 against the SECURE version ===")
say("  Result   : %s"%search_secure(payload))
say("Valid input still works: %s"%search_secure("Laptop Pro"))
open("sqli_output.txt","w").write("\n".join(out))
