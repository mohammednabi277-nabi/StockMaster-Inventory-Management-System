-- StockMaster Inventory Management System : DDL
-- Executed on SQLite 3.45 (portable ANSI-style types; see notes for PostgreSQL/MySQL).
PRAGMA foreign_keys = ON;

CREATE TABLE category (
    category_id    INTEGER      PRIMARY KEY,
    category_name  VARCHAR(50)  NOT NULL UNIQUE
);

CREATE TABLE supplier (
    supplier_id    INTEGER      PRIMARY KEY,
    supplier_name  VARCHAR(80)  NOT NULL UNIQUE,
    contact_email  VARCHAR(100) NOT NULL UNIQUE,
    phone          VARCHAR(20),
    city           VARCHAR(50)
);

CREATE TABLE product (
    product_id     INTEGER       PRIMARY KEY,
    product_sku    VARCHAR(20)   NOT NULL UNIQUE,
    product_name   VARCHAR(100)  NOT NULL,
    category_id    INTEGER       NOT NULL REFERENCES category(category_id),
    unit_price     DECIMAL(10,2) NOT NULL CHECK (unit_price > 0),
    unit_volume    DECIMAL(8,2)  NOT NULL CHECK (unit_volume > 0),   -- cubic feet per unit
    reorder_point  INTEGER       NOT NULL CHECK (reorder_point >= 0)
);

CREATE TABLE warehouse (
    warehouse_id   INTEGER      PRIMARY KEY,
    warehouse_name VARCHAR(80)  NOT NULL UNIQUE,
    city           VARCHAR(50)  NOT NULL,
    state          VARCHAR(30)  NOT NULL,
    capacity       DECIMAL(12,2) NOT NULL CHECK (capacity > 0)       -- total cubic feet
);

CREATE TABLE product_supplier (                 -- resolves M:N Product <-> Supplier
    product_id     INTEGER NOT NULL REFERENCES product(product_id),
    supplier_id    INTEGER NOT NULL REFERENCES supplier(supplier_id),
    PRIMARY KEY (product_id, supplier_id)
);

CREATE TABLE stock (                            -- resolves M:N Product <-> Warehouse
    product_id     INTEGER NOT NULL REFERENCES product(product_id),
    warehouse_id   INTEGER NOT NULL REFERENCES warehouse(warehouse_id),
    quantity       INTEGER NOT NULL CHECK (quantity >= 0),
    last_updated   DATE    NOT NULL,
    PRIMARY KEY (product_id, warehouse_id)
);

CREATE TABLE customer (
    customer_id    INTEGER      PRIMARY KEY,
    customer_name  VARCHAR(80)  NOT NULL,
    email          VARCHAR(100) NOT NULL UNIQUE,
    city           VARCHAR(50)
);

CREATE TABLE purchase_order (                   -- INBOUND
    po_id          INTEGER     PRIMARY KEY,
    supplier_id    INTEGER     NOT NULL REFERENCES supplier(supplier_id),
    warehouse_id   INTEGER     NOT NULL REFERENCES warehouse(warehouse_id),
    order_date     DATE        NOT NULL,
    expected_date  DATE        NOT NULL,
    delivered_date DATE,
    status         VARCHAR(12) NOT NULL CHECK (status IN ('Ordered','Delivered','Cancelled')),
    CHECK (expected_date >= order_date),
    CHECK (delivered_date IS NULL OR delivered_date >= order_date)
);

CREATE TABLE purchase_order_item (
    po_id          INTEGER NOT NULL REFERENCES purchase_order(po_id),
    product_id     INTEGER NOT NULL REFERENCES product(product_id),
    quantity       INTEGER NOT NULL CHECK (quantity > 0),
    unit_cost      DECIMAL(10,2) NOT NULL CHECK (unit_cost > 0),
    PRIMARY KEY (po_id, product_id)
);

CREATE TABLE sales_order (                      -- OUTBOUND
    so_id          INTEGER     PRIMARY KEY,
    customer_id    INTEGER     NOT NULL REFERENCES customer(customer_id),
    warehouse_id   INTEGER     NOT NULL REFERENCES warehouse(warehouse_id),
    order_date     DATE        NOT NULL,
    ship_date      DATE,
    status         VARCHAR(12) NOT NULL CHECK (status IN ('Placed','Shipped','Cancelled')),
    CHECK (ship_date IS NULL OR ship_date >= order_date)
);

CREATE TABLE sales_order_item (
    so_id          INTEGER NOT NULL REFERENCES sales_order(so_id),
    product_id     INTEGER NOT NULL REFERENCES product(product_id),
    quantity       INTEGER NOT NULL CHECK (quantity > 0),
    unit_price     DECIMAL(10,2) NOT NULL CHECK (unit_price > 0),
    PRIMARY KEY (so_id, product_id)
);

CREATE TABLE sales_return (
    return_id      INTEGER PRIMARY KEY,
    so_id          INTEGER NOT NULL,
    product_id     INTEGER NOT NULL,
    quantity       INTEGER NOT NULL CHECK (quantity > 0),
    return_date    DATE    NOT NULL,
    reason         VARCHAR(60),
    FOREIGN KEY (so_id, product_id) REFERENCES sales_order_item(so_id, product_id)
);

CREATE TABLE stock_transfer_log (
    log_id         INTEGER PRIMARY KEY,
    product_id     INTEGER NOT NULL REFERENCES product(product_id),
    from_wh        INTEGER NOT NULL REFERENCES warehouse(warehouse_id),
    to_wh          INTEGER NOT NULL REFERENCES warehouse(warehouse_id),
    quantity       INTEGER NOT NULL CHECK (quantity > 0),
    transfer_time  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status         VARCHAR(12) NOT NULL DEFAULT 'COMPLETED',
    CHECK (from_wh <> to_wh)
);
