-- Stock Daddy: Inventory Management System
-- Schema v6
--
-- Scope: closes two gaps flagged against v5 while reviewing Section VIII of
-- the proposal - REQ-11 and REQ-23 currently have no data to be implemented
-- against. No engine change, no changes to v5's auth columns.
--
-- Changes from v5 (schema_v5.sql):
--
--   1. item_movement.from_status, item_movement.to_status
--      REQ-11: "track whether an item is in storage or in use... as tools
--      and supplies leave and return to the storage unit." Before this
--      change, item_movement only recorded location changes
--      (from_storage_id/to_storage_id). A pure status change - an item
--      going In Storage -> In Use with no location change at all - wrote
--      no row anywhere. Only item.item_status held the *current* value;
--      there was no history of how it got there. Both columns are
--      nullable: a location-only move (the existing v1-v5 behavior)
--      leaves them NULL, a status-only change leaves from/to_storage_id
--      NULL instead, and a row can set both if a move and a status change
--      happen together. This keeps the single append-only table rather
--      than splitting movement and status history into two tables that
--      would need to be re-merged to answer "what happened to this item,
--      in order."
--
--   2. item_type.service_life_days
--      REQ-23: "flag items exceeding a configured age or service life for
--      their item type." item.date_added already gives an item's age;
--      nothing previously defined the threshold to compare it against.
--      Nullable, following the same convention replacement_cost already
--      established: NULL means no service-life limit is configured for
--      that type, not zero days. An item type with no limit set is simply
--      never flagged for this reason.
--
-- Earlier history (v1 through v5): see schema_v5.sql's header for the
-- MySQL->SQLite port notes and v1-v5 changes; unchanged here.
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
  item_type_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  name              VARCHAR(100) NOT NULL UNIQUE,
  description       VARCHAR(255),
  -- Cost to acquire one new unit. NULL = acquisition unavailable (c_k = inf).
  replacement_cost  DECIMAL(10,2) NULL,
  -- REQ-23. NULL = no service-life limit configured for this type (not zero).
  service_life_days INTEGER NULL,
  CONSTRAINT chk_replacement_cost_positive
    CHECK (replacement_cost IS NULL OR replacement_cost > 0),
  CONSTRAINT chk_service_life_positive
    CHECK (service_life_days IS NULL OR service_life_days > 0)
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
  from_storage_id   INTEGER NULL,   -- NULL if item was newly added, or this row is a status-only change
  to_storage_id     INTEGER NULL,   -- NULL if item is departing storage, or this row is a status-only change
  -- REQ-11. NULL/NULL together = a location-only move (v1-v5 behavior); a
  -- status change with no location change sets these instead, leaving
  -- from/to_storage_id NULL. A row can set both kinds at once.
  from_status       VARCHAR(100) NULL,
  to_status         VARCHAR(100) NULL,
  moved_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (item_id) REFERENCES item(item_id),
  FOREIGN KEY (from_storage_id) REFERENCES storage(storage_id),
  FOREIGN KEY (to_storage_id) REFERENCES storage(storage_id),
  CONSTRAINT chk_movement_status_values CHECK (
    (from_status IS NULL OR from_status IN ('In Storage', 'In Use', 'In Transit')) AND
    (to_status   IS NULL OR to_status   IN ('In Storage', 'In Use', 'In Transit'))
  ),
  -- A row has to record something happening: a location change, a status
  -- change, or both. All four columns NULL would be a movement of nothing.
  CONSTRAINT chk_movement_records_something CHECK (
    from_storage_id IS NOT NULL OR to_storage_id IS NOT NULL OR
    from_status     IS NOT NULL OR to_status     IS NOT NULL
  )
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
