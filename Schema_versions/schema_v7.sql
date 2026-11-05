-- Stock Daddy: Inventory Management System
-- Schema v7
--
-- Scope: the team agreed (Discord, Oct 25-Nov 1) on these additions before
-- freezing the schema ahead of the API migration for Version 2. No engine
-- change, no changes to existing v1-v6 columns - purely additive.
--
-- Changes from v6 (schema_v6.sql):
--
--   1. retired DATETIME NULL on business, building, room, storage, item
--      A location or item can be retired without being deleted, so its
--      history (item_movement rows, past target_quantity rows) stays
--      intact. NULL = active, a timestamp = retired, following the same
--      "NULL means not in that state" convention as replacement_cost and
--      service_life_days. "Block until empty" (a room/building can't be
--      retired while anything is still inside it) is enforced by the
--      application, not a CHECK constraint here - a constraint can't see
--      across tables (whether a room's storages are empty) without a
--      trigger, and the team agreed this is API-level validation, not a
--      schema rule.
--
--   2. business_member (owner_id, business_id, role)
--      Replaces the implicit assumption that a business has exactly one
--      owner. role is 'owner' or 'employee'. business.owner_id is left
--      unchanged for this version - existing owner-scoped queries in
--      frontend/db.py keep working unmodified. business_member is what
--      the API's new role-aware access check (require_role, Section 14a)
--      is built against going forward; migrating frontend/db.py's own
--      queries off business.owner_id and onto business_member is API
--      migration work, not a schema concern, and is explicitly out of
--      scope for this version.
--
--   3. plan_run (one row per saved optimizer run)
--      The team decided to add this now rather than risk a v8 later,
--      since it is cheap to add and expensive to retrofit (every existing
--      optimizer caller would need updating to read a cached plan vs.
--      solving fresh). Stores the plan itself as JSON (plan_json) rather
--      than normalizing trips into rows - the plan's shape is Scott's
--      Optimizer.models.Plan, which this schema has no reason to mirror
--      structurally; JSON keeps the two independent.
--
--   4. v_building_item_type_counts, v_building_item_type_position
--      Both views now exclude retired items, storage, rooms, and
--      buildings. Without this, a retired empty building's target_quantity
--      rows would still report a shortage, and the optimizer would send a
--      truck to a building nobody can receive it at - the exact bug Scott
--      flagged on Nov 1.
--
-- Earlier history (v1 through v6): see schema_v6.sql's header for prior
-- changes and the MySQL->SQLite port notes; unchanged here.

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
  -- NULL = active. See header note 1.
  retired     DATETIME NULL,
  FOREIGN KEY (owner_id) REFERENCES owners(owner_id)
);

-- Who can access a business, beyond the single owner business.owner_id
-- already names. Every current owner is backfilled as role='owner' in
-- seed_data_v7.sql; new employee accounts are added here, not as a second
-- owners.owner_id on business.
CREATE TABLE business_member (
  business_member_id INTEGER PRIMARY KEY AUTOINCREMENT,
  business_id         INTEGER NOT NULL,
  owner_id             INTEGER NOT NULL,
  role                 VARCHAR(20) NOT NULL,
  FOREIGN KEY (business_id) REFERENCES business(business_id),
  FOREIGN KEY (owner_id) REFERENCES owners(owner_id),
  UNIQUE (business_id, owner_id),
  CONSTRAINT chk_member_role CHECK (role IN ('owner', 'employee'))
);

CREATE TABLE building (
  building_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  business_id     INTEGER NOT NULL,
  state           VARCHAR(100),
  city            VARCHAR(100),
  street_address  VARCHAR(100),
  retired         DATETIME NULL,
  FOREIGN KEY (business_id) REFERENCES business(business_id)
);

CREATE TABLE room (
  room_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  building_id INTEGER NOT NULL,
  location    VARCHAR(100),
  retired     DATETIME NULL,
  FOREIGN KEY (building_id) REFERENCES building(building_id)
);

CREATE TABLE storage (
  storage_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  room_id       INTEGER NOT NULL,
  storage_type  VARCHAR(100),
  retired       DATETIME NULL,
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
  retired      DATETIME NULL,
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

-- One row per saved optimizer run (team decision, Nov 1 - see header note
-- 3). plan_json holds the solved Plan verbatim so this table needs no
-- schema change if Optimizer.models.Plan's shape changes later.
CREATE TABLE plan_run (
  plan_run_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  business_id    INTEGER NOT NULL,
  run_by         INTEGER NOT NULL,
  created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
  method         VARCHAR(50) NOT NULL,
  total_cost     DECIMAL(12,2) NOT NULL,
  baseline_cost  DECIMAL(12,2) NOT NULL,
  -- Optimality gap as a fraction (0 = proven optimal, 0.1 = within 10%).
  gap            DECIMAL(6,4) NOT NULL,
  plan_json      TEXT NOT NULL,
  FOREIGN KEY (business_id) REFERENCES business(business_id),
  FOREIGN KEY (run_by) REFERENCES owners(owner_id),
  CONSTRAINT chk_plan_costs_nonneg CHECK (total_cost >= 0 AND baseline_cost >= 0),
  CONSTRAINT chk_plan_gap_range CHECK (gap >= 0 AND gap <= 1)
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
-- In Transit items belong to no building and appear in neither. Retired
-- items, storage, rooms, and buildings are excluded throughout (v7) - see
-- header note 4.
CREATE VIEW v_building_item_type_counts AS
SELECT
  r.building_id,
  i.item_type_id,
  COUNT(*)                                                     AS present_qty,
  SUM(CASE WHEN i.item_status = 'In Storage' THEN 1 ELSE 0 END) AS available_qty
FROM item i
JOIN storage  s  ON s.storage_id  = i.storage_id
JOIN room     r  ON r.room_id     = s.room_id
JOIN building bl ON bl.building_id = r.building_id
WHERE i.item_status <> 'In Transit'
  AND i.retired  IS NULL
  AND s.retired  IS NULL
  AND r.retired  IS NULL
  AND bl.retired IS NULL
GROUP BY r.building_id, i.item_type_id;

-- A building/type with counted stock but no target row is included (second
-- branch) with an implicit target of 0, instead of being silently dropped
-- (the v3->v4 bug fix). SQLite has no FULL OUTER JOIN, same as MySQL, so
-- this is the two LEFT JOINs a full outer join would compile to, combined
-- with UNION ALL. The branches are disjoint by construction (first = pairs
-- with a target row, second = pairs without), so UNION ALL cannot introduce
-- duplicates. The first branch also excludes retired buildings (v7) - a
-- target row left over for a retired building must not report a shortage.
-- The second branch needs no separate retired check: it only ever contains
-- buildings that already passed through v_building_item_type_counts, which
-- excludes retired buildings itself.
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
JOIN building bl ON bl.building_id = t.building_id AND bl.retired IS NULL
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
CREATE INDEX idx_business_member_owner    ON business_member (owner_id);
