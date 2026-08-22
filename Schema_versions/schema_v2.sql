-- Stock Daddy: Inventory Management System
-- Schema v2
--
-- Changes from v1 (Schema_versions/initial_db_creation_v1.sql):
--   - Split DDL (this file) from sample/seed data (see seed_data_v2.sql)
--   - Removed denormalized columns (BUSINESS.owner_name, BUILDING.business_name/owner_name) -
--     these are derivable via FK joins and were a source of drift
--   - Fixed bug: BUILDING.owner_id FK incorrectly referenced business(owner_id) instead of owners(owner_id)
--   - Replaced STORAGE.item_cnt trigger-maintained counter with a view (v_storage_item_count)
--     computed via COUNT(), removing the need for the three item_cnt triggers
--   - Added tables needed for Scott's inventory-transfer optimization problem:
--       ITEM_TYPE            - category an item belongs to (separate from a specific Item)
--       TARGET_QUANTITY      - desired quantity of an item type per building
--       ITEM_MOVEMENT        - append-only movement log (item / from / to / timestamp)
--     ITEM.item_status now includes 'In Transit' as a valid state (enforced via CHECK)
--   - ITEM.storage_id is now nullable to represent an item mid-transit (not currently in any storage)

CREATE DATABASE IF NOT EXISTS inventory_management;
USE inventory_management;

-- ---------------------------------------------------------------------------
-- Core hierarchy: owners -> business -> building -> room -> storage -> item
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

-- A category of item (e.g. "Nail Gun"), as distinct from a specific physical Item.
-- Needed so we can talk about "3 nail guns" at the optimizer level before
-- picking which specific 3 to move.
CREATE TABLE item_type (
  item_type_id INT AUTO_INCREMENT PRIMARY KEY,
  name         VARCHAR(100) NOT NULL UNIQUE,
  description  VARCHAR(255)
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
-- Optimization support: target stock levels + movement history
-- ---------------------------------------------------------------------------

-- Desired quantity of a given item type at a given building.
-- Optimizer compares this against actual on-hand counts (see v_building_item_type_counts)
-- to decide what should move where.
CREATE TABLE target_quantity (
  target_quantity_id INT AUTO_INCREMENT PRIMARY KEY,
  building_id         INT NOT NULL,
  item_type_id        INT NOT NULL,
  target_qty          INT NOT NULL,
  FOREIGN KEY (building_id) REFERENCES building(building_id),
  FOREIGN KEY (item_type_id) REFERENCES item_type(item_type_id),
  UNIQUE (building_id, item_type_id)
);

-- Append-only movement log. Every move of an item creates a new row here rather
-- than just overwriting item.storage_id, so full movement history is preserved
-- for the owner and for the optimizer's cost model.
CREATE TABLE item_movement (
  item_movement_id INT AUTO_INCREMENT PRIMARY KEY,
  item_id           INT NOT NULL,
  from_storage_id   INT NULL,   -- NULL if item was newly added rather than moved
  to_storage_id     INT NULL,   -- NULL if item is departing storage (e.g. going out with a crew)
  moved_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (item_id) REFERENCES item(item_id),
  FOREIGN KEY (from_storage_id) REFERENCES storage(storage_id),
  FOREIGN KEY (to_storage_id) REFERENCES storage(storage_id)
);

-- ---------------------------------------------------------------------------
-- Views (replace v1's trigger-maintained counters with computed values)
-- ---------------------------------------------------------------------------

-- Current item count per storage unit, computed on demand instead of maintained
-- by INSERT/UPDATE/DELETE triggers.
CREATE VIEW v_storage_item_count AS
SELECT
  s.storage_id,
  COUNT(i.item_id) AS item_cnt
FROM storage s
LEFT JOIN item i ON i.storage_id = s.storage_id
GROUP BY s.storage_id;

-- On-hand quantity of each item type per building, for the optimizer to compare
-- against target_quantity.
CREATE VIEW v_building_item_type_counts AS
SELECT
  r.building_id,
  i.item_type_id,
  COUNT(i.item_id) AS on_hand_qty
FROM item i
JOIN storage s ON s.storage_id = i.storage_id
JOIN room r ON r.room_id = s.room_id
WHERE i.item_status != 'In Transit'
GROUP BY r.building_id, i.item_type_id;
