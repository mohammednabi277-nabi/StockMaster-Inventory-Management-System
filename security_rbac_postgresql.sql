-- =====================================================================
-- StockMaster : Role-Based Access Control (PostgreSQL syntax)
-- NOTE: written for PostgreSQL 14+. It was NOT executed in the sandbox used to
-- prepare this report (SQLite has no GRANT/REVOKE) - run it in psql / pgAdmin
-- and take your screenshots from that session.
-- =====================================================================
-- 0. Reporting views the Manager / Sales roles read from
CREATE VIEW v_stock_report AS
  SELECT p.product_sku, p.product_name, w.city, s.quantity, p.reorder_point
  FROM stock s JOIN product p USING (product_id) JOIN warehouse w USING (warehouse_id);

CREATE VIEW v_stock_availability AS            -- what the Sales Team may see
  SELECT p.product_name, SUM(s.quantity) AS available_qty
  FROM stock s JOIN product p USING (product_id) GROUP BY p.product_name;

-- 1. Roles (no direct login; users inherit them)
CREATE ROLE admin_role;
CREATE ROLE manager_role;
CREATE ROLE auditor_role;
CREATE ROLE sales_role;

-- 2. Privileges
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO admin_role;

GRANT SELECT, UPDATE ON stock               TO manager_role;
GRANT SELECT          ON v_stock_report     TO manager_role;
GRANT SELECT, INSERT  ON stock_transfer_log TO manager_role;   -- needed by the transfer transaction
GRANT SELECT          ON product, warehouse TO manager_role;

GRANT SELECT ON stock_transfer_log TO auditor_role;            -- inventory logs only

GRANT SELECT ON v_stock_availability TO sales_role;            -- view stock, cannot modify

-- 3. Login users
CREATE USER alice_admin  PASSWORD 'Str0ng!Adm1n' IN ROLE admin_role;
CREATE USER bob_manager  PASSWORD 'Str0ng!Mgr9'  IN ROLE manager_role;
CREATE USER carol_audit  PASSWORD 'Str0ng!Aud7'  IN ROLE auditor_role;
CREATE USER dave_sales   PASSWORD 'Str0ng!Sal3'  IN ROLE sales_role;

-- 4. Enforcement tests ------------------------------------------------
SET ROLE bob_manager;
UPDATE stock SET quantity = quantity - 1 WHERE product_id = 1 AND warehouse_id = 1;  -- OK
DELETE FROM stock WHERE product_id = 1;      -- expected: ERROR: permission denied for table stock
SELECT * FROM v_stock_report LIMIT 3;        -- OK
RESET ROLE;

SET ROLE carol_audit;
SELECT * FROM stock_transfer_log;            -- OK
UPDATE stock SET quantity = 0;               -- expected: ERROR: permission denied for table stock
SELECT * FROM stock;                         -- expected: ERROR: permission denied for table stock
RESET ROLE;

SET ROLE dave_sales;
SELECT * FROM v_stock_availability LIMIT 3;  -- OK
UPDATE stock SET quantity = 999;             -- expected: ERROR: permission denied for table stock
RESET ROLE;

-- 5. REVOKE demonstration
REVOKE UPDATE ON stock FROM manager_role;
SET ROLE bob_manager;
UPDATE stock SET quantity = quantity + 1 WHERE product_id = 1 AND warehouse_id = 1;  -- expected: permission denied
RESET ROLE;
GRANT UPDATE ON stock TO manager_role;       -- restore
