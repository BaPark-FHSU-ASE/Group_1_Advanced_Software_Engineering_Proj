-- Stock Daddy: sample/seed data for schema_v2.sql
-- Run schema_v2.sql first.
--
-- Models the roofing-company example from team discussion: one owner/business
-- with two buildings (North, South), several item types, and a stock imbalance
-- between buildings so Scott's optimizer has something real to work with -
-- North has extra nail guns, South is short.

USE inventory_management;

-- ---------------------------------------------------------------------------
-- Owner / business
-- ---------------------------------------------------------------------------

INSERT INTO owners (first_name, last_name)
VALUES ('Bens_Test_FirstNm2', 'Bens_Test_LastNm2');   -- owner_id 1

INSERT INTO business (name, owner_id)
VALUES ('Bens_Test_Roofing', 1);                       -- business_id 1

-- ---------------------------------------------------------------------------
-- Buildings, rooms, storage
-- ---------------------------------------------------------------------------

INSERT INTO building (business_id, state, city, street_address)
VALUES
  (1, 'Kansas', 'Salina', '458 North Test Street'),     -- building_id 1 (North)
  (1, 'Kansas', 'Salina', '900 South Test Street');     -- building_id 2 (South)

INSERT INTO room (building_id, location)
VALUES
  (1, 'North main storage closet'),                     -- room_id 1
  (1, 'North safety equipment room'),                   -- room_id 2
  (2, 'South main storage closet'),                      -- room_id 3
  (2, 'South safety equipment room');                    -- room_id 4

INSERT INTO storage (room_id, storage_type)
VALUES
  (1, 'Locker'),        -- storage_id 1  (North / main)
  (1, 'Shelf'),          -- storage_id 2  (North / main)
  (2, 'Storage Unit'),   -- storage_id 3  (North / safety)
  (3, 'Locker'),         -- storage_id 4  (South / main)
  (4, 'Toolbox');        -- storage_id 5  (South / safety)

-- ---------------------------------------------------------------------------
-- Item types
-- ---------------------------------------------------------------------------

INSERT INTO item_type (name, description)
VALUES
  ('Nail Gun', 'Pneumatic or electric nail gun'),        -- item_type_id 1
  ('Ladder', 'Extension or step ladder'),                -- item_type_id 2
  ('Hard Hat', 'Safety helmet'),                          -- item_type_id 3
  ('Roofing Hammer', 'Standard roofing hatchet/hammer');  -- item_type_id 4

-- ---------------------------------------------------------------------------
-- Items: North has 5 nail guns (2 idle), South has 1 (short by 2)
-- ---------------------------------------------------------------------------

INSERT INTO item (item_type_id, storage_id, item_name, item_status)
VALUES
  -- North nail guns (storage 1) - 5 total, 2 idle/in storage, 3 in use
  (1, 1, 'Nail Gun #1', 'In Storage'),
  (1, 1, 'Nail Gun #2', 'In Storage'),
  (1, 1, 'Nail Gun #3', 'In Use'),
  (1, 1, 'Nail Gun #4', 'In Use'),
  (1, 1, 'Nail Gun #5', 'In Use'),
  -- South nail gun (storage 4) - only 1, short of its target
  (1, 4, 'Nail Gun #6', 'In Storage'),

  -- Ladders split across both buildings
  (2, 2, 'Ladder #1', 'In Storage'),
  (2, 2, 'Ladder #2', 'In Storage'),
  (2, 5, 'Ladder #3', 'In Storage'),

  -- Hard hats, mostly at South where the active crew is
  (3, 3, 'Hard Hat #1', 'In Storage'),
  (3, 5, 'Hard Hat #2', 'In Use'),
  (3, 5, 'Hard Hat #3', 'In Use'),
  (3, 5, 'Hard Hat #4', 'In Use'),

  -- One roofing hammer currently in transit between buildings
  (4, NULL, 'Roofing Hammer #1', 'In Transit');

-- ---------------------------------------------------------------------------
-- Target quantities per building (what each site *should* have on hand)
-- ---------------------------------------------------------------------------

INSERT INTO target_quantity (building_id, item_type_id, target_qty)
VALUES
  (1, 1, 3),   -- North should have 3 nail guns (currently has 5 -> 2 idle surplus)
  (2, 1, 3),   -- South should have 3 nail guns (currently has 1 -> short by 2)
  (1, 2, 2),   -- North should have 2 ladders (has 2 -> on target)
  (2, 2, 2),   -- South should have 2 ladders (has 1 -> short by 1)
  (1, 3, 1),   -- North should have 1 hard hat (has 1 -> on target)
  (2, 3, 3),   -- South should have 3 hard hats (has 3 -> on target)
  (1, 4, 1),   -- North should have 1 roofing hammer
  (2, 4, 1);   -- South should have 1 roofing hammer

-- ---------------------------------------------------------------------------
-- Movement history: initial placements + one recorded transfer + the in-transit hammer
-- ---------------------------------------------------------------------------

-- Initial placement for every item (from_storage_id NULL = newly added)
INSERT INTO item_movement (item_id, from_storage_id, to_storage_id)
SELECT item_id, NULL, storage_id
FROM item
WHERE storage_id IS NOT NULL;

-- Example completed transfer: Nail Gun #2 was moved from North's shelf (storage 2)
-- into the main locker (storage 1) last week, before this seed data was written.
INSERT INTO item_movement (item_id, from_storage_id, to_storage_id, moved_at)
VALUES (2, 2, 1, DATE_SUB(NOW(), INTERVAL 7 DAY));

-- The in-transit roofing hammer: departed North's safety room (storage 3),
-- not yet arrived anywhere (to_storage_id NULL, item_status = 'In Transit').
INSERT INTO item_movement (item_id, from_storage_id, to_storage_id)
VALUES (14, 3, NULL);

-- ---------------------------------------------------------------------------
-- Sanity checks
-- ---------------------------------------------------------------------------

SELECT * FROM item ORDER BY item_id;
SELECT * FROM v_storage_item_count ORDER BY storage_id;
SELECT * FROM v_building_item_type_counts ORDER BY building_id, item_type_id;

-- Surplus/shortage per building & item type, comparing on-hand to target -
-- this is effectively what Scott's optimizer would start from.
SELECT
  t.building_id,
  t.item_type_id,
  it.name AS item_type_name,
  t.target_qty,
  COALESCE(c.on_hand_qty, 0) AS on_hand_qty,
  COALESCE(c.on_hand_qty, 0) - t.target_qty AS surplus_or_shortage
FROM target_quantity t
JOIN item_type it ON it.item_type_id = t.item_type_id
LEFT JOIN v_building_item_type_counts c
  ON c.building_id = t.building_id AND c.item_type_id = t.item_type_id
ORDER BY t.building_id, t.item_type_id;
