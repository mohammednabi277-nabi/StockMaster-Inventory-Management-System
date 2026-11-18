-- Indexing strategy for StockMaster
CREATE INDEX idx_product_sku          ON product(product_sku);
CREATE INDEX idx_stock_warehouse      ON stock(warehouse_id);
CREATE INDEX idx_ps_supplier          ON product_supplier(supplier_id);
CREATE INDEX idx_po_supplier_status   ON purchase_order(supplier_id, status, delivered_date);
CREATE INDEX idx_return_product       ON sales_return(product_id, quantity);
CREATE INDEX idx_soi_product          ON sales_order_item(product_id);
