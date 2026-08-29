-- Stock Daddy: Inventory Management System
-- Schema v5
--
-- Engine change: ported from MySQL to SQLite (team decision, 8/26 - no
-- server to install, `sqlite3` ships with Python, and everyone gets a
-- working DB just by cloning the repo). This is the same v5 content that
-- was drafted against MySQL - real auth via owners.email/password_hash -
-- just re-expressed in SQLite's dialect. See "Porting notes" below for
-- what actually differs.
--
-- Changes from v4 (schema_v4.sql, MySQL):
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
-- Porting notes (MySQL -> SQLite):
--
--   - No CREATE DATABASE / USE: SQLite is one file, not a server with
--     named databases. See Schema_versions/build_db.py, which points
--     sqlite3 at a .db file path instead.
--   - AUTO_INCREMENT -> INTEGER PRIMARY KEY AUTOINCREMENT. SQLite requires
--     the column type to be exactly INTEGER (not INT) for this to work.
--   - Generated columns need the GENERATED ALWAYS keyword that MySQL didn't
--     require (building_route.handling_cost_per_unit).
--   - COMMENT '...' on columns isn't supported in SQLite - converted to
--     plain SQL comments instead. No behavior change, just moved the note.
--   - Foreign keys are NOT enforced by SQLite unless the connection turns
--     them on explicitly (PRAGMA foreign_keys = ON). The FOREIGN KEY
--     clauses below are still required for this to have any effect, but
--     enforcement is the application's job now - see db.py's get_connection().
--   - DECIMAL(p,s): SQLite has no fixed-point decimal storage class - a
--     DECIMAL column here gets NUMERIC affinity and is actually stored as
--     a floating-point REAL. For the money/rate columns in this schema
--     (replacement_cost, fixed_dispatch_cost, cost_per_unit_mile,
--     distance_miles, handling_cost_per_unit, target_qty) that's a real
--     precision tradeoff versus MySQL's exact DECIMAL, worth knowing if
--     the optimizer ever compares costs for exact equality rather than
--     with a tolerance.
--
-- No separate MySQL-version-required note: this file has no CHECK-support
-- version dependency the way the MySQL versions did - SQLite has enforced
-- CHECK constraints since 3.3.0 (2006).

-- ---------------------------------------------------------------------------
-- Core hierarchy: owners -> business -> building -> room -> storage -> item
-- ---------------------------------------------------------------------------

CREATE TABLE owners (
  owner_id       INTEGER PRIMARY KEY AUTOINCREMENT,
  first_name     VARCHAR(100) NOT NULL,
  last_name      VARCHAR(100) NOT NULL,
  -- Login credentials. password_hash must never hold a plaintext password -
  -- see the frontend's db.py for how it's written/checked.
  email          VARCHAR(255) NOT NULL UNIQUE,
  password_hash  VARCHAR(255) NOT NULL,
  date_added     DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE business (
  business_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name        VARCHAR(100) NOT NULL,
  owner_id    INTEGER NOT NULL,
  FOREIGN KEY (owner_id) REFERENCES owners(owner_id)
);

CREATE TABLE building (
  building_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  business_id     INTEGER NOT NULL,
  state           VARCHAR(100),
  city            VARCHAR(100),
  street_address  VARCHAR(100),
  FOREIGN KEY (business_id) REFERENCES business(business_id)
);

CREATE TABLE room (
  room_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  building_id INTEGER NOT NULL,
  location    VARCHAR(100),
  FOREIGN KEY (building_id) REFERENCES building(building_id)
);

CREATE TABLE storage (
  storage_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  room_id       INTEGER NOT NULL,
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
  item_type_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  name             VARCHAR(100) NOT NULL UNIQUE,
  description      VARCHAR(255),
  -- Cost to acquire one new unit. NULL = acquisition unavailable (c_k = inf).
  replacement_cost DECIMAL(10,2) NULL,
  CONSTRAINT chk_replacement_cost_positive
    CHECK (replacement_cost IS NULL OR replacement_cost > 0)
);

CREATE TABLE item (
  item_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  item_type_id INTEGER NOT NULL,
  storage_id   INTEGER NULL,      -- nullable: NULL while item_status = 'In Transit'
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
  target_quantity_id INTEGER PRIMARY KEY AUTOINCREMENT,
  building_id         INTEGER NOT NULL,
  item_type_id        INTEGER NOT NULL,
  target_qty          INTEGER NOT NULL,
  FOREIGN KEY (building_id) REFERENCES building(building_id),
  FOREIGN KEY (item_type_id) REFERENCES item_type(item_type_id),
  UNIQUE (building_id, item_type_id),
  CONSTRAINT chk_target_nonneg CHECK (target_qty >= 0)
);

CREATE TABLE item_movement (
  item_movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id           INTEGER NOT NULL,
  from_storage_id   INTEGER NULL,   -- NULL if item was newly added rather than moved
  to_storage_id     INTEGER NULL,   -- NULL if item is departing storage
  moved_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (item_id) REFERENCES item(item_id),
  FOREIGN KEY (from_storage_id) REFERENCES storage(storage_id),
  FOREIGN KEY (to_storage_id) REFERENCES storage(storage_id)
);

-- Fixed-charge transportation costs. f_ij is charged once per trip whatever
-- the load; h_ij scales with units carried. Rows are directional.
CREATE TABLE building_route (
  building_route_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  from_building_id       INTEGER NOT NULL,
  to_building_id         INTEGER NOT NULL,
  distance_miles         DECIMAL(8,2) NOT NULL,
  -- f_ij: charged once if the route is opened, whatever it carries.
  fixed_dispatch_cost    DECIMAL(10,2) NOT NULL,
  cost_per_unit_mile     DECIMAL(10,4) NOT NULL,
  -- h_ij: cost to move one unit along this route. SQLite needs the
  -- GENERATED ALWAYS keyword that MySQL didn't require here.
  handling_cost_per_unit DECIMAL(12,4)
    GENERATED ALWAYS AS (distance_miles * cost_per_unit_mile) STORED,
  FOREIGN KEY (from_building_id) REFERENCES building(building_id),
  FOREIGN KEY (to_building_id) REFERENCES building(building_id),
  UNIQUE (from_building_id, to_building_id),
  CONSTRAINT chk_route_distinct CHECK (from_building_id <> to_building_id),
  CONSTRAINT chk_dispatch_positive CHECK (fixed_dispatch_cost > 0),
  CONSTRAINT chk_rate_nonneg CHECK (cost_per_unit_mile >= 0 AND distance_miles >= 0)
);

-- ---------------------------------------------------------------------------
-- Views
-- ---------------------------------------------------------------------------

CREATE VIEW v_storage_item_count AS
SELECT
  s.storage_id,
  COUNT(i.item_id) AS item_cnt
FROM storage s
LEFT JOIN item i ON i.storage_id = s.storage_id
GROUP BY s.storage_id;

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

-- A building/type with counted stock but no target row is included (second
-- branch) with an implicit target of 0, instead of being silently dropped
-- (the v3->v4 bug fix). SQLite has no FULL OUTER JOIN, same as MySQL, so
-- this is the two LEFT JOINs a full outer join would compile to, combined
-- with UNION ALL. The branches are disjoint by construction (first = pairs
-- with a target row, second = pairs without), so UNION ALL cannot introduce
-- duplicates.
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
  MAX(t.target_qty - COALESCE(c.present_qty, 0), 0) AS shortage_qty,
  MIN(
    MAX(COALESCE(c.present_qty, 0) - t.target_qty, 0),
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
  c.available_qty AS shippable_surplus_qty  -- MIN(MAX(P-0,0), A) reduces to A
FROM v_building_item_type_counts c
LEFT JOIN target_quantity t
       ON c.building_id  = t.building_id
      AND c.item_type_id = t.item_type_id
WHERE t.target_quantity_id IS NULL;

-- ---------------------------------------------------------------------------
-- Indexes for the optimizer's read path
-- ---------------------------------------------------------------------------

CREATE INDEX idx_item_type_storage_status ON item (item_type_id, storage_id, item_status);
CREATE INDEX idx_storage_room             ON storage (room_id);
CREATE INDEX idx_room_building            ON room (building_id);
