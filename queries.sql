-- ===================== BASIC QUERIES =====================
-- @Q1 | List all products under the "Electronics" category
SELECT p.product_id, p.product_sku, p.product_name, p.unit_price
FROM product p
JOIN category c ON c.category_id = p.category_id
WHERE c.category_name = 'Electronics'
ORDER BY p.product_id;

-- @Q2 | Find warehouses located in "Texas"
SELECT warehouse_id, warehouse_name, city, state, capacity
FROM warehouse
WHERE state = 'Texas';

-- @Q3 | Retrieve suppliers who provide "Laptops"
SELECT DISTINCT s.supplier_id, s.supplier_name
FROM supplier s
JOIN product_supplier ps ON ps.supplier_id = s.supplier_id
JOIN product p           ON p.product_id   = ps.product_id
WHERE p.product_name LIKE 'Laptop%'
ORDER BY s.supplier_id;

-- @Q4 | List products with a unit price greater than $500
SELECT product_id, product_name, unit_price
FROM product
WHERE unit_price > 500
ORDER BY unit_price DESC;

-- @Q5 | Find stock entries updated "Today"
SELECT product_id, warehouse_id, quantity, last_updated
FROM stock
WHERE last_updated = date('now')
ORDER BY warehouse_id, product_id;

-- ===================== JOINS & SUBQUERIES =====================
-- @Q6 | Stock levels with Product Name and Warehouse Location
SELECT p.product_name, w.city || ', ' || w.state AS warehouse_location, s.quantity
FROM stock s
JOIN product   p ON p.product_id   = s.product_id
JOIN warehouse w ON w.warehouse_id = s.warehouse_id
ORDER BY w.warehouse_id, p.product_id;

-- @Q7a | TechGlobal products that are out of stock (JOIN + GROUP BY version)
SELECT p.product_id, p.product_name
FROM product p
JOIN product_supplier ps ON ps.product_id = p.product_id
JOIN supplier su         ON su.supplier_id = ps.supplier_id
LEFT JOIN stock st       ON st.product_id = p.product_id
WHERE su.supplier_name = 'TechGlobal'
GROUP BY p.product_id, p.product_name
HAVING COALESCE(SUM(st.quantity), 0) = 0
ORDER BY p.product_id;

-- @Q7b | TechGlobal products that are out of stock (subquery / NOT EXISTS version)
SELECT p.product_id, p.product_name
FROM product p
WHERE p.product_id IN (SELECT ps.product_id FROM product_supplier ps
                       JOIN supplier su ON su.supplier_id = ps.supplier_id
                       WHERE su.supplier_name = 'TechGlobal')
  AND NOT EXISTS (SELECT 1 FROM stock st
                  WHERE st.product_id = p.product_id AND st.quantity > 0)
ORDER BY p.product_id;

-- @Q8a | Warehouses holding stock for "Smartphones" (JOIN version)
SELECT DISTINCT w.warehouse_id, w.warehouse_name, w.city
FROM warehouse w
JOIN stock st   ON st.warehouse_id = w.warehouse_id
JOIN product p  ON p.product_id    = st.product_id
WHERE p.product_name LIKE 'Smartphone%' AND st.quantity > 0
ORDER BY w.warehouse_id;

-- @Q8b | Warehouses holding stock for "Smartphones" (subquery version)
SELECT warehouse_id, warehouse_name, city
FROM warehouse
WHERE warehouse_id IN (SELECT st.warehouse_id FROM stock st
                       WHERE st.quantity > 0
                         AND st.product_id IN (SELECT product_id FROM product
                                               WHERE product_name LIKE 'Smartphone%'))
ORDER BY warehouse_id;

-- @Q9 | Products with active reorder alerts (Quantity < Reorder Point)
SELECT p.product_name, w.city AS warehouse, s.quantity, p.reorder_point
FROM stock s
JOIN product   p ON p.product_id   = s.product_id
JOIN warehouse w ON w.warehouse_id = s.warehouse_id
WHERE s.quantity < p.reorder_point
ORDER BY (p.reorder_point - s.quantity) DESC;

-- @Q10a | Suppliers with no delivery in the last 3 months (NOT EXISTS version)
SELECT s.supplier_id, s.supplier_name
FROM supplier s
WHERE NOT EXISTS (SELECT 1 FROM purchase_order po
                  WHERE po.supplier_id = s.supplier_id
                    AND po.status = 'Delivered'
                    AND po.delivered_date >= date('now','-3 months'))
ORDER BY s.supplier_id;

-- @Q10b | Suppliers with no delivery in the last 3 months (LEFT JOIN version)
SELECT s.supplier_id, s.supplier_name
FROM supplier s
LEFT JOIN purchase_order po
       ON po.supplier_id = s.supplier_id
      AND po.status = 'Delivered'
      AND po.delivered_date >= date('now','-3 months')
WHERE po.po_id IS NULL
ORDER BY s.supplier_id;

-- ===================== AGGREGATION & REPORTS =====================
-- @Q11 | Top 5 warehouses by total value of inventory held
SELECT w.warehouse_name, w.city, ROUND(SUM(s.quantity * p.unit_price), 2) AS inventory_value
FROM warehouse w
JOIN stock   s ON s.warehouse_id = w.warehouse_id
JOIN product p ON p.product_id   = s.product_id
GROUP BY w.warehouse_id
ORDER BY inventory_value DESC
LIMIT 5;

-- @Q12 | Total quantity of stock available per product category
SELECT c.category_name, SUM(s.quantity) AS total_quantity
FROM category c
JOIN product p ON p.category_id = c.category_id
JOIN stock   s ON s.product_id  = p.product_id
GROUP BY c.category_id
ORDER BY total_quantity DESC;

-- @Q13 | Supplier with the shortest average delivery time
SELECT s.supplier_name,
       ROUND(AVG(julianday(po.delivered_date) - julianday(po.order_date)), 2) AS avg_delivery_days
FROM purchase_order po
JOIN supplier s ON s.supplier_id = po.supplier_id
WHERE po.status = 'Delivered'
GROUP BY s.supplier_id
ORDER BY avg_delivery_days ASC
LIMIT 1;

-- @Q14 | Month with the highest number of inbound purchase orders
SELECT strftime('%Y-%m', order_date) AS month, COUNT(*) AS inbound_orders
FROM purchase_order
GROUP BY month
ORDER BY inbound_orders DESC
LIMIT 1;

-- @Q15 | Average stock turnover rate per product (units shipped in last 12 months / average stock on hand)
SELECT p.product_name,
       sold.units_sold_12m,
       stk.total_stock                                   AS stock_on_hand,
       ROUND(1.0 * sold.units_sold_12m / stk.total_stock, 2) AS turnover_rate
FROM product p
JOIN (SELECT soi.product_id, SUM(soi.quantity) AS units_sold_12m
      FROM sales_order_item soi
      JOIN sales_order so ON so.so_id = soi.so_id
      WHERE so.status = 'Shipped' AND so.order_date >= date('now','-12 months')
      GROUP BY soi.product_id) sold ON sold.product_id = p.product_id
JOIN (SELECT product_id, SUM(quantity) AS total_stock
      FROM stock GROUP BY product_id HAVING SUM(quantity) > 0) stk ON stk.product_id = p.product_id
ORDER BY turnover_rate DESC
LIMIT 10;

-- ===================== ADVANCED QUERIES =====================
-- @Q16 | Daily stock movement report (Product, Inbound Qty, Outbound Qty) - last 5 days
SELECT mv_date, product_name, SUM(inbound) AS inbound_qty, SUM(outbound) AS outbound_qty
FROM (
  SELECT po.delivered_date AS mv_date, p.product_name, poi.quantity AS inbound, 0 AS outbound
  FROM purchase_order po
  JOIN purchase_order_item poi ON poi.po_id = po.po_id
  JOIN product p ON p.product_id = poi.product_id
  WHERE po.status = 'Delivered'
  UNION ALL
  SELECT so.ship_date, p.product_name, 0, soi.quantity
  FROM sales_order so
  JOIN sales_order_item soi ON soi.so_id = so.so_id
  JOIN product p ON p.product_id = soi.product_id
  WHERE so.status = 'Shipped'
)
WHERE mv_date >= date('now','-5 days')
GROUP BY mv_date, product_name
ORDER BY mv_date DESC, product_name;

-- @Q17a | Products available in ALL warehouses (GROUP BY / HAVING version)
SELECT p.product_id, p.product_name
FROM product p
JOIN stock s ON s.product_id = p.product_id AND s.quantity > 0
GROUP BY p.product_id, p.product_name
HAVING COUNT(DISTINCT s.warehouse_id) = (SELECT COUNT(*) FROM warehouse)
ORDER BY p.product_id;

-- @Q17b | Products available in ALL warehouses (double NOT EXISTS version)
SELECT p.product_id, p.product_name
FROM product p
WHERE NOT EXISTS (
  SELECT 1 FROM warehouse w
  WHERE NOT EXISTS (SELECT 1 FROM stock s
                    WHERE s.product_id = p.product_id
                      AND s.warehouse_id = w.warehouse_id
                      AND s.quantity > 0))
ORDER BY p.product_id;

-- @Q18 | Warehouses running at over 90% capacity
SELECT w.warehouse_name, w.city, ROUND(w.capacity,0) AS capacity_cuft,
       ROUND(SUM(s.quantity * p.unit_volume),0) AS used_cuft,
       ROUND(100.0 * SUM(s.quantity * p.unit_volume) / w.capacity, 1) AS utilization_pct
FROM warehouse w
JOIN stock   s ON s.warehouse_id = w.warehouse_id
JOIN product p ON p.product_id   = s.product_id
GROUP BY w.warehouse_id
HAVING utilization_pct > 90;

-- @Q19 | Items returned (Sales Return) more than 10 times
SELECT p.product_name, COUNT(*) AS return_count, SUM(r.quantity) AS units_returned
FROM sales_return r
JOIN product p ON p.product_id = r.product_id
GROUP BY p.product_id
HAVING COUNT(*) > 10
ORDER BY return_count DESC;

-- @Q20 | View: Product Name, Total Global Stock, Supplier Name
CREATE VIEW v_product_global_stock AS
SELECT p.product_name,
       COALESCE(g.total_stock, 0) AS total_global_stock,
       su.supplier_name
FROM product p
LEFT JOIN (SELECT product_id, SUM(quantity) AS total_stock FROM stock GROUP BY product_id) g
       ON g.product_id = p.product_id
JOIN product_supplier ps ON ps.product_id = p.product_id
JOIN supplier su         ON su.supplier_id = ps.supplier_id;

-- @Q20b | Using the view
SELECT * FROM v_product_global_stock ORDER BY total_global_stock DESC, product_name LIMIT 8;

-- ===================== BUSINESS INSIGHTS (Supply-chain manager) =====================
-- @I1 | Dead stock: products with stock on hand but no sale in the last 6 months
SELECT p.product_id, p.product_name, SUM(st.quantity) AS units_on_hand,
       ROUND(SUM(st.quantity * p.unit_price),2) AS value_tied_up
FROM product p
JOIN stock st ON st.product_id = p.product_id
WHERE NOT EXISTS (SELECT 1 FROM sales_order_item soi
                  JOIN sales_order so ON so.so_id = soi.so_id
                  WHERE soi.product_id = p.product_id
                    AND so.order_date >= date('now','-6 months'))
GROUP BY p.product_id
HAVING SUM(st.quantity) > 0
ORDER BY value_tied_up DESC;

-- @I2 | Warehouse utilization (capacity vs used space) - all warehouses
SELECT w.warehouse_name, ROUND(w.capacity,0) AS capacity_cuft,
       ROUND(SUM(s.quantity * p.unit_volume),0) AS used_cuft,
       ROUND(100.0 * SUM(s.quantity * p.unit_volume) / w.capacity, 1) AS utilization_pct
FROM warehouse w
JOIN stock s   ON s.warehouse_id = w.warehouse_id
JOIN product p ON p.product_id   = s.product_id
GROUP BY w.warehouse_id
ORDER BY utilization_pct DESC;

-- @I3 | High-demand products needing urgent restock (30-day sales vs total stock = days of cover)
SELECT p.product_name,
       SUM(soi.quantity)                                    AS sold_last_30d,
       (SELECT SUM(quantity) FROM stock WHERE product_id = p.product_id) AS stock_on_hand,
       ROUND(1.0 * (SELECT SUM(quantity) FROM stock WHERE product_id = p.product_id)
             / (SUM(soi.quantity) / 30.0), 1)                AS days_of_cover
FROM product p
JOIN sales_order_item soi ON soi.product_id = p.product_id
JOIN sales_order so       ON so.so_id = soi.so_id
WHERE so.order_date >= date('now','-30 days') AND so.status <> 'Cancelled'
GROUP BY p.product_id
HAVING days_of_cover < 60
ORDER BY days_of_cover ASC
LIMIT 8;

-- @I4 | Supplier performance report (delivery-time accuracy)
SELECT s.supplier_name,
       COUNT(*)                                                               AS delivered_orders,
       ROUND(AVG(julianday(po.delivered_date) - julianday(po.order_date)),1) AS avg_days,
       ROUND(100.0 * SUM(po.delivered_date <= po.expected_date) / COUNT(*),1) AS on_time_pct,
       ROUND(AVG(julianday(po.delivered_date) - julianday(po.expected_date)),1) AS avg_delay_days
FROM purchase_order po
JOIN supplier s ON s.supplier_id = po.supplier_id
WHERE po.status = 'Delivered'
GROUP BY s.supplier_id
ORDER BY on_time_pct DESC;
