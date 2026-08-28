-- Stock Daddy: Inventory Management System
-- Schema v5
--
-- Scope: adds real authentication data. No changes to v4's optimizer fixes.
--
-- Changes from v4 (schema_v4.sql):
--
--   1. owners.email, owners.password_hash
--      There was previously no way to actually log in as an owner - the
--      frontend used a hardcoded admin/admin stub because the schema had
--      nowhere to store credentials. email is the login identifier (UNIQUE,
--      so two owners can't register with the same address); password_hash
--      stores a hashed password (werkzeug's generate_password_hash in the
--      frontend, scrypt-based) - never a plaintext password. Both are
--      NOT NULL: an owner record with no way to log in isn't useful, so
--      every owner is expected to go through registration, not be inserted
--      directly without credentials.
--
-- Requires MySQL 8.0.16 or later (unchanged from v4): earlier versions
-- parse CHECK constraints and silently ignore them.

CREATE DATABASE IF NOT EXISTS inventory_management;
USE inventory_management;

-- ---------------------------------------------------------------------------
-- Core hierarchy: owners -> business -> building -> room -> storage -> item
-- ---------------------------------------------------------------------------

CREATE TABLE owners (
  owner_id       INT AUTO_INCREMENT PRIMARY KEY,
  first_name     VARCHAR(100) NOT NULL,
  last_name      VARCHAR(100) NOT NULL,
  -- CHANGE 1: login credentials. password_hash must never hold a plaintext
  -- password - see the frontend's db.py for how it's written/checked.
  email          VARCHAR(255) NOT NULL UNIQUE,
  password_hash  VARCHAR(255) NOT NULL,
  date_added     DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE business (
  business_id INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(100) NOT NULL,
  owner_id    INT NOT NULL,
  FOREIGN KEY (owner_id) REFERENCES owners(owner_id)
);

CREATE TABLE building (
  building_id     INT AUTO_INCREMENT PRIMARY KEY,
  business_id     INT NOT NULL,
  state           VARCHAR(100),
  city            VARCHAR(100),
  street_address  VARCHAR(100),
  FOREIGN KEY (business_id) REFERENCES business(business_id)
);

CREATE TABLE room (
  room_id     INT AUTO_INCREMENT PRIMARY KEY,
  building_id INT NOT NULL,
  location    VARCHAR(100),
  FOREIGN KEY (building_id) REFERENCES building(building_id)
);

CREATE TABLE storage (
  storage_id    INT AUTO_INCREMENT PRIMARY KEY,
  room_id       INT NOT NULL,
  storage_type  VARCHAR(100),
  FOREIGN KEY (room_id) REFERENCES room(room_id)
);

-- ---------------------------------------------------------------------------
-- Item types & items
-- ---------------------------------------------------------------------------

-- A category of item (e.g. "Nail Gun"), as distinct from a specific physical
-- Item. The optimizer works at the type level ("move 3 nail guns"); picking
-- which specific 3 is a separate step afterwards.
CREATE TABLE item_type (
  item_type_id     INT AUTO_INCREMENT PRIMARY KEY,
  name             VARCHAR(100) NOT NULL UNIQUE,
  description      VARCHAR(255),
  replacement_cost DECIMAL(10,2) NULL
    COMMENT 'Cost to acquire one new unit. NULL = acquisition unavailable (c_k = inf).',
  -- CHANGE 2: c_k in R>0 union {infinity} per the math doc; NULL still means infinity.
  CONSTRAINT chk_replacement_cost_positive
    CHECK (replacement_cost IS NULL OR replacement_cost > 0)
);

CREATE TABLE item (
  item_id      INT AUTO_INCREMENT PRIMARY KEY,
  item_type_id INT NOT NULL,
  storage_id   INT NULL,          -- nullable: NULL while item_status = 'In Transit'
  item_name    VARCHAR(100),
  item_status  VARCHAR(100) NOT NULL DEFAULT 'In Storage',
  date_added   DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (item_type_id) REFERENCES item_type(item_type_id),
  FOREIGN KEY (storage_id) REFERENCES storage(storage_id),
  CONSTRAINT chk_item_status CHECK (item_status IN ('In Storage', 'In Use', 'In Transit'))
);

-- ---------------------------------------------------------------------------
-- Optimization support: target stock levels, route costs, movement history
-- ---------------------------------------------------------------------------

CREATE TABLE target_quantity (
  target_quantity_id INT AUTO_INCREMENT PRIMARY KEY,
  building_id        INT NOT NULL,
  item_type_id        INT NOT NULL,
  target_qty          INT NOT NULL,
  FOREIGN KEY (building_id) REFERENCES building(building_id),
  FOREIGN KEY (item_type_id) REFERENCES item_type(item_type_id),
  UNIQUE (building_id, item_type_id),
  CONSTRAINT chk_target_nonneg CHECK (target_qty >= 0)
);

CREATE TABLE item_movement (
  item_movement_id INT AUTO_INCREMENT PRIMARY KEY,
  item_id           INT NOT NULL,
  from_storage_id   INT NULL,   -- NULL if item was newly added rather than moved
  to_storage_id     INT NULL,   -- NULL if item is departing storage
  moved_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (item_id) REFERENCES item(item_id),
  FOREIGN KEY (from_storage_id) REFERENCES storage(storage_id),
  FOREIGN KEY (to_storage_id) REFERENCES storage(storage_id)
);

-- Fixed-charge transportation costs. f_ij is charged once per trip whatever
-- the load; h_ij scales with units carried. Rows are directional.
CREATE TABLE building_route (
  building_route_id      INT AUTO_INCREMENT PRIMARY KEY,
  from_building_id       INT NOT NULL,
  to_building_id         INT NOT NULL,
  distance_miles         DECIMAL(8,2) NOT NULL,
  fixed_dispatch_cost    DECIMAL(10,2) NOT NULL
    COMMENT 'f_ij: charged once if the route is opened, whatever it carries.',
  cost_per_unit_mile     DECIMAL(10,4) NOT NULL,
  handling_cost_per_unit DECIMAL(12,4)
    AS (distance_miles * cost_per_unit_mile) STORED
    COMMENT 'h_ij: cost to move one unit along this route.',
  FOREIGN KEY (from_building_id) REFERENCES building(building_id),
  FOREIGN KEY (to_building_id) REFERENCES building(building_id),
  UNIQUE (from_building_id, to_building_id),
  CONSTRAINT chk_route_distinct CHECK (from_building_id <> to_building_id),
  -- CHANGE 2: f_ij in R>0, h_ij in R>=0 per the math doc.
  CONSTRAINT chk_dispatch_positive CHECK (fixed_dispatch_cost > 0),
  CONSTRAINT chk_rate_nonneg CHECK (cost_per_unit_mile >= 0 AND distance_miles >= 0)
);

-- ---------------------------------------------------------------------------
-- Views
-- ---------------------------------------------------------------------------

-- Unchanged from v3.
CREATE VIEW v_storage_item_count AS
SELECT
  s.storage_id,
  COUNT(i.item_id) AS item_cnt
FROM storage s
LEFT JOIN item i ON i.storage_id = s.storage_id
GROUP BY s.storage_id;

-- Unchanged from v3.
--   present_qty   - everything the building holds, In Storage or In Use.
--                   Shortage is measured against this.
--   available_qty - only what is idle, and therefore all that can ship.
--
-- In Transit items belong to no building and appear in neither.
CREATE VIEW v_building_item_type_counts AS
SELECT
  r.building_id,
  i.item_type_id,
  COUNT(*)                                                     AS present_qty,
  SUM(CASE WHEN i.item_status = 'In Storage' THEN 1 ELSE 0 END) AS available_qty
FROM item i
JOIN storage s ON s.storage_id = i.storage_id
JOIN room    r ON r.room_id    = s.room_id
WHERE i.item_status <> 'In Transit'
GROUP BY r.building_id, i.item_type_id;

-- CHANGE 1: a building/type with counted stock but no target row is now
-- included (second branch) with an implicit target of 0, instead of being
-- silently dropped. MySQL has no FULL OUTER JOIN, so this is the two
-- LEFT JOINs a full outer join would compile to, combined with UNION ALL.
-- The branches are disjoint by construction (first = pairs with a target
-- row, second = pairs without), so UNION ALL cannot introduce duplicates.
--
--   shortage_qty          = d_jk
--   shippable_surplus_qty = s_ik
CREATE VIEW v_building_item_type_position AS
SELECT
  t.building_id,
  t.item_type_id,
  t.target_qty,
  COALESCE(c.present_qty, 0)   AS present_qty,
  COALESCE(c.available_qty, 0) AS available_qty,
  GREATEST(t.target_qty - COALESCE(c.present_qty, 0), 0) AS shortage_qty,
  LEAST(
    GREATEST(COALESCE(c.present_qty, 0) - t.target_qty, 0),
    COALESCE(c.available_qty, 0)
  ) AS shippable_surplus_qty
FROM target_quantity t
LEFT JOIN v_building_item_type_counts c
       ON c.building_id  = t.building_id
      AND c.item_type_id = t.item_type_id

UNION ALL

SELECT
  c.building_id,
  c.item_type_id,
  0 AS target_qty,
  c.present_qty,
  c.available_qty,
  0 AS shortage_qty,                 -- target defaults to 0, so P - 0 can't be a shortage
  c.available_qty AS shippable_surplus_qty  -- LEAST(GREATEST(P-0,0), A) reduces to A
FROM v_building_item_type_counts c
LEFT JOIN target_quantity t
       ON c.building_id  = t.building_id
      AND c.item_type_id = t.item_type_id
WHERE t.target_quantity_id IS NULL;

-- ---------------------------------------------------------------------------
-- Indexes for the optimizer's read path (unchanged from v3)
-- ---------------------------------------------------------------------------

CREATE INDEX idx_item_type_storage_status ON item (item_type_id, storage_id, item_status);
CREATE INDEX idx_storage_room             ON storage (room_id);
CREATE INDEX idx_room_building            ON room (building_id);
