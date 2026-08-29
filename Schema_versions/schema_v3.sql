-- Stock Daddy: Inventory Management System
-- Schema v3
--
-- Scope: this version adds only what the redistribution optimizer needs.
-- Other gaps found while reviewing v2 against our requirements list
-- (authentication, per-business item types, storage types as data, item
-- retirement, service life, in-transit destinations) are deliberately NOT
-- here. They are filed as issues so they can be argued and scheduled on
-- their own rather than riding along with the optimizer work.
--
-- Changes from v2 (schema_v2.sql):
--
--   1. ITEM_TYPE.replacement_cost
--      The parameter c_k in the cost model. What it costs to acquire one new
--      unit. NULL means acquisition is unavailable for that type, so every
--      shortage of it must be filled by transfer - the strict formulation,
--      and the default for any type left blank.
--
--   2. BUILDING_ROUTE.handling_cost_per_unit
--      The parameter h_ij, generated from distance * rate so the two cannot
--      drift apart and the optimizer reads one value instead of multiplying.
--
--   3. v_building_item_type_counts: on_hand_qty split into present_qty and
--      available_qty.  *** This is a correctness fix, not a feature. ***
--      v2 counted 'In Storage' and 'In Use' together. The optimizer needs
--      them apart:
--        - shortage is measured against what a building HAS. A site whose
--          three nail guns are all out on a job is not short; it owns three.
--        - shippable surplus is capped by what is IDLE, because an in-use
--          item cannot be loaded onto a truck.
--      One number for both yields either plans that cannot be executed, or
--      phantom shortages that ship equipment to a site already holding enough.
--      BREAKING: on_hand_qty no longer exists. Grep for it before merging.
--
--   4. v_building_item_type_position (new)
--      Hands the optimizer d_jk and s_ik directly, so the solver does not
--      reimplement the surplus/shortage arithmetic.
--
--   5. chk_target_nonneg on target_quantity
--      A negative target would inflate shippable surplus and produce plans
--      that cannot be executed. One line, guards s_ik.
--
--   6. Indexes on the optimizer's read path. v2 had none.
--
-- Requires MySQL 8.0.16 or later. Earlier versions parse CHECK constraints
-- and silently ignore them, which would defeat chk_item_status as well.

CREATE DATABASE IF NOT EXISTS inventory_management;
USE inventory_management;

-- ---------------------------------------------------------------------------
-- Core hierarchy: owners -> business -> building -> room -> storage -> item
-- (unchanged from v2)
-- ---------------------------------------------------------------------------

CREATE TABLE owners (
  owner_id    INT AUTO_INCREMENT PRIMARY KEY,
  first_name  VARCHAR(100) NOT NULL,
  last_name   VARCHAR(100) NOT NULL,
  date_added  DATETIME DEFAULT CURRENT_TIMESTAMP
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
  -- CHANGE 1: c_k. NULL = acquisition unavailable, shortage must be transferred.
  replacement_cost DECIMAL(10,2) NULL
    COMMENT 'Cost to acquire one new unit. NULL = acquisition unavailable (c_k = inf).'
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
  -- CHANGE 5: a negative target would inflate shippable surplus.
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
  -- CHANGE 2: h_ij, generated so it cannot drift from its two factors.
  handling_cost_per_unit DECIMAL(12,4)
    AS (distance_miles * cost_per_unit_mile) STORED
    COMMENT 'h_ij: cost to move one unit along this route.',
  FOREIGN KEY (from_building_id) REFERENCES building(building_id),
  FOREIGN KEY (to_building_id) REFERENCES building(building_id),
  UNIQUE (from_building_id, to_building_id),
  CONSTRAINT chk_route_distinct CHECK (from_building_id <> to_building_id)
);

-- ---------------------------------------------------------------------------
-- Views
-- ---------------------------------------------------------------------------

-- Unchanged from v2.
CREATE VIEW v_storage_item_count AS
SELECT
  s.storage_id,
  COUNT(i.item_id) AS item_cnt
FROM storage s
LEFT JOIN item i ON i.storage_id = s.storage_id
GROUP BY s.storage_id;

-- CHANGE 3: two quantities where v2 had one.
--
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

-- CHANGE 4: the optimizer's input in one place.
--   shortage_qty          = d_jk
--   shippable_surplus_qty = s_ik
--
-- Surplus takes the lesser of surplus-over-target and what is idle: five nail
-- guns against a target of three is a surplus of two, but if only one is In
-- Storage then only one can ship.
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
      AND c.item_type_id = t.item_type_id;

-- ---------------------------------------------------------------------------
-- CHANGE 6: indexes for the optimizer's read path
-- ---------------------------------------------------------------------------

CREATE INDEX idx_item_type_storage_status ON item (item_type_id, storage_id, item_status);
CREATE INDEX idx_storage_room             ON storage (room_id);
CREATE INDEX idx_room_building            ON room (building_id);
