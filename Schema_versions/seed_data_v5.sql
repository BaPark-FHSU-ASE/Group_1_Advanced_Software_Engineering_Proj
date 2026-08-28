-- Stock Daddy: seed data for schema_v5.sql
-- Run schema_v5.sql first.
--
-- Unchanged from seed_data_v4.sql other than the owner insert now including
-- email/password_hash (schema v5 made both NOT NULL) and this header.
--
-- Test login for this seed owner:
--   email:    dale@prairieroofing.example
--   password: roofing123
-- (password_hash below is werkzeug's generate_password_hash('roofing123'))
--
-- Prairie Roofing & Exteriors: five Kansas sites, six item types, 92 items.
-- Built so the optimizer has non-trivial work, and solved exactly beforehand
-- so the expected results at the bottom of this file are known-correct.
--
-- What this instance exercises:
--   * nearest-source-first opens 7 trips at $1,072.19; the optimum opens 3
--     at $575.44 - a 46.3% gap
--   * hard hats are BOUGHT at Abilene and MOVED to Hays and Great Bend in the
--     same plan. Same item type, opposite decision, purely because a truck was
--     already going to those two
--   * Salina North holds 4 surplus nail guns but can ship only 3: the fourth
--     is In Use. This is the case v2's single on_hand_qty column got wrong
--   * hard hats are exactly tight - 7 shippable against 7 short
--   * one item is In Transit and must appear in no count anywhere

USE inventory_management;

-- --------------------------------------------------------------------
-- Owner and business
-- --------------------------------------------------------------------
INSERT INTO owners (first_name, last_name, email, password_hash)
VALUES ('Dale', 'Renner', 'dale@prairieroofing.example',
        'scrypt:32768:8:1$uL5DPd0xFaetSy1W$d66a5a46ed9d22aaa659aa169b4cf70ee3fa51a13d390f1b50923e1bdc345b6842454901a4568e32c6af9859fdd8ebb19487ebb630593656afdc150579e107a1');
                                               -- owner_id 1

INSERT INTO business (name, owner_id)
VALUES ('Prairie Roofing & Exteriors', 1);    -- business_id 1

-- --------------------------------------------------------------------
-- Buildings, rooms, storage
--
-- Distances span 9 to 118 miles. The spread matters: it is what makes the
-- fixed dispatch charge dominate on some routes and not others.
-- --------------------------------------------------------------------
INSERT INTO building (business_id, state, city, street_address) VALUES
  (1, 'Kansas', 'Salina', '458 N Ohio Street'),       -- building_id 1 (Salina North)
  (1, 'Kansas', 'Salina', '900 S Broadway Blvd'),     -- building_id 2 (Salina South)
  (1, 'Kansas', 'Abilene', '1204 NW 3rd Street'),     -- building_id 3 (Abilene)
  (1, 'Kansas', 'Hays', '2815 Vine Street'),          -- building_id 4 (Hays)
  (1, 'Kansas', 'Great Bend', '710 McKinley Street'); -- building_id 5 (Great Bend)

INSERT INTO room (building_id, location) VALUES
  (1, 'Salina North main storage'),               -- room_id 1
  (1, 'Salina North safety equipment room'),      -- room_id 2
  (2, 'Salina South main storage'),               -- room_id 3
  (2, 'Salina South safety equipment room'),      -- room_id 4
  (3, 'Abilene main storage'),                    -- room_id 5
  (3, 'Abilene safety equipment room'),           -- room_id 6
  (4, 'Hays main storage'),                       -- room_id 7
  (4, 'Hays safety equipment room'),              -- room_id 8
  (5, 'Great Bend main storage'),                 -- room_id 9
  (5, 'Great Bend safety equipment room');        -- room_id 10

-- storage_type stays free text, per NF Req 1's list of five.
INSERT INTO storage (room_id, storage_type) VALUES
  (1, 'Locker'),              -- storage_id 1
  (1, 'Shelf'),               -- storage_id 2
  (2, 'Storage Unit'),        -- storage_id 3
  (3, 'Locker'),              -- storage_id 4
  (4, 'Toolbox'),             -- storage_id 5
  (5, 'Closet'),              -- storage_id 6
  (6, 'Storage Unit'),        -- storage_id 7
  (7, 'Locker'),              -- storage_id 8
  (8, 'Shelf'),               -- storage_id 9
  (9, 'Closet'),              -- storage_id 10
  (10, 'Toolbox');            -- storage_id 11

-- --------------------------------------------------------------------
-- Item types
--
-- replacement_cost is c_k. Hard hats are cheap enough that buying beats
-- opening a route for them alone; the machines are not. NULL would mean
-- acquisition is unavailable for that type (the strict formulation).
-- --------------------------------------------------------------------
INSERT INTO item_type (name, description, replacement_cost) VALUES
  ('Nail Gun', 'Pneumatic or electric nail gun', 340.00),     -- item_type_id 1
  ('Air Compressor', 'Portable air compressor', 620.00),      -- item_type_id 2
  ('Extension Ladder', 'Extension or step ladder', 290.00),   -- item_type_id 3
  ('Hard Hat', 'Safety helmet', 38.00),                       -- item_type_id 4
  ('Safety Harness', 'Fall-protection harness', 145.00),      -- item_type_id 5
  ('Tear-off Shovel', 'Roofing tear-off shovel', 42.00);      -- item_type_id 6

-- --------------------------------------------------------------------
-- Items
-- --------------------------------------------------------------------
INSERT INTO item (item_type_id, storage_id, item_name, item_status) VALUES
  -- Salina North
  (1, 1, 'Nail Gun #1', 'In Storage'),
  (1, 1, 'Nail Gun #2', 'In Storage'),
  (1, 1, 'Nail Gun #3', 'In Storage'),
  (1, 1, 'Nail Gun #4', 'In Use'),
  (1, 1, 'Nail Gun #5', 'In Use'),
  (1, 1, 'Nail Gun #6', 'In Use'),
  (1, 1, 'Nail Gun #7', 'In Use'),
  (2, 1, 'Air Compressor #1', 'In Storage'),
  (2, 1, 'Air Compressor #2', 'In Use'),
  (3, 2, 'Extension Ladder #1', 'In Storage'),
  (3, 2, 'Extension Ladder #2', 'In Storage'),
  (3, 2, 'Extension Ladder #3', 'In Storage'),
  (3, 2, 'Extension Ladder #4', 'In Storage'),
  (4, 3, 'Hard Hat #1', 'In Storage'),
  (4, 3, 'Hard Hat #2', 'In Storage'),
  (4, 3, 'Hard Hat #3', 'In Storage'),
  (4, 3, 'Hard Hat #4', 'In Storage'),
  (4, 3, 'Hard Hat #5', 'In Storage'),
  (4, 3, 'Hard Hat #6', 'In Storage'),
  (4, 3, 'Hard Hat #7', 'In Storage'),
  (4, 3, 'Hard Hat #8', 'In Use'),
  (4, 3, 'Hard Hat #9', 'In Use'),
  (4, 3, 'Hard Hat #10', 'In Use'),
  (4, 3, 'Hard Hat #11', 'In Use'),
  (5, 3, 'Safety Harness #1', 'In Storage'),
  (5, 3, 'Safety Harness #2', 'In Storage'),
  (5, 3, 'Safety Harness #3', 'In Storage'),
  (5, 3, 'Safety Harness #4', 'In Storage'),
  (5, 3, 'Safety Harness #5', 'In Use'),
  (5, 3, 'Safety Harness #6', 'In Use'),
  (5, 3, 'Safety Harness #7', 'In Use'),
  (5, 3, 'Safety Harness #8', 'In Use'),
  (6, 2, 'Tear-off Shovel #1', 'In Storage'),
  (6, 2, 'Tear-off Shovel #2', 'In Storage'),
  (6, 2, 'Tear-off Shovel #3', 'In Storage'),
  (6, 2, 'Tear-off Shovel #4', 'In Storage'),
  (6, 2, 'Tear-off Shovel #5', 'In Storage'),
  (6, 2, 'Tear-off Shovel #6', 'In Use'),
  (6, 2, 'Tear-off Shovel #7', 'In Use'),
  (6, 2, 'Tear-off Shovel #8', 'In Use'),
  -- Salina South
  (1, 4, 'Nail Gun #8', 'In Storage'),
  (1, 4, 'Nail Gun #9', 'In Storage'),
  (1, 4, 'Nail Gun #10', 'In Storage'),
  (1, 4, 'Nail Gun #11', 'In Storage'),
  (2, 4, 'Air Compressor #3', 'In Use'),
  (3, 4, 'Extension Ladder #5', 'In Storage'),
  (3, 4, 'Extension Ladder #6', 'In Storage'),
  (3, 4, 'Extension Ladder #7', 'In Storage'),
  (4, 5, 'Hard Hat #12', 'In Storage'),
  (4, 5, 'Hard Hat #13', 'In Storage'),
  (4, 5, 'Hard Hat #14', 'In Storage'),
  (4, 5, 'Hard Hat #15', 'In Storage'),
  (5, 5, 'Safety Harness #9', 'In Use'),
  (5, 5, 'Safety Harness #10', 'In Use'),
  (6, 4, 'Tear-off Shovel #9', 'In Storage'),
  (6, 4, 'Tear-off Shovel #10', 'In Storage'),
  (6, 4, 'Tear-off Shovel #11', 'In Storage'),
  (6, 4, 'Tear-off Shovel #12', 'In Storage'),
  (6, 4, 'Tear-off Shovel #13', 'In Storage'),
  -- Abilene
  (1, 6, 'Nail Gun #12', 'In Storage'),
  (1, 6, 'Nail Gun #13', 'In Storage'),
  (1, 6, 'Nail Gun #14', 'In Storage'),
  (1, 6, 'Nail Gun #15', 'In Storage'),
  (2, 6, 'Air Compressor #4', 'In Storage'),
  (2, 6, 'Air Compressor #5', 'In Storage'),
  (3, 6, 'Extension Ladder #8', 'In Storage'),
  (3, 6, 'Extension Ladder #9', 'In Storage'),
  (4, 7, 'Hard Hat #16', 'In Storage'),
  (5, 7, 'Safety Harness #11', 'In Storage'),
  (5, 7, 'Safety Harness #12', 'In Storage'),
  (5, 7, 'Safety Harness #13', 'In Storage'),
  (5, 7, 'Safety Harness #14', 'In Storage'),
  (5, 7, 'Safety Harness #15', 'In Storage'),
  (6, 6, 'Tear-off Shovel #14', 'In Storage'),
  (6, 6, 'Tear-off Shovel #15', 'In Storage'),
  -- Hays
  (1, 8, 'Nail Gun #16', 'In Use'),
  (3, 8, 'Extension Ladder #10', 'In Storage'),
  (3, 8, 'Extension Ladder #11', 'In Storage'),
  (3, 8, 'Extension Ladder #12', 'In Storage'),
  (4, 9, 'Hard Hat #17', 'In Storage'),
  (5, 9, 'Safety Harness #16', 'In Storage'),
  (5, 9, 'Safety Harness #17', 'In Storage'),
  (5, 9, 'Safety Harness #18', 'In Storage'),
  (6, 8, 'Tear-off Shovel #16', 'In Storage'),
  -- Great Bend
  (1, 10, 'Nail Gun #17', 'In Use'),
  (2, 10, 'Air Compressor #6', 'In Storage'),
  (3, 10, 'Extension Ladder #13', 'In Storage'),
  (4, 11, 'Hard Hat #18', 'In Storage'),
  (5, 11, 'Safety Harness #19', 'In Storage'),
  (6, 10, 'Tear-off Shovel #17', 'In Storage'),
  (6, 10, 'Tear-off Shovel #18', 'In Storage'),
  -- In Transit: left Salina North, not yet arrived. Counted at neither site.
  (2, NULL, 'Air Compressor #99', 'In Transit');

-- --------------------------------------------------------------------
-- Target quantities - what each site should hold
-- --------------------------------------------------------------------
INSERT INTO target_quantity (building_id, item_type_id, target_qty) VALUES
  (1, 1, 3),
  (1, 2, 1),
  (1, 3, 2),
  (1, 4, 4),
  (1, 5, 4),
  (1, 6, 3),
  (2, 1, 3),
  (2, 2, 2),
  (2, 3, 2),
  (2, 4, 4),
  (2, 5, 4),
  (2, 6, 3),
  (3, 1, 2),
  (3, 2, 1),
  (3, 3, 2),
  (3, 4, 3),
  (3, 5, 3),
  (3, 6, 2),
  (4, 1, 3),
  (4, 2, 1),
  (4, 3, 2),
  (4, 4, 4),
  (4, 5, 3),
  (4, 6, 3),
  (5, 1, 2),
  (5, 2, 1),
  (5, 3, 2),
  (5, 4, 3),
  (5, 5, 2),
  (5, 6, 2);

-- --------------------------------------------------------------------
-- Route costs: dispatch = $60 + $1.20/mile, handling = $0.05/unit/mile
--
-- All 20 ordered pairs are present. A missing pair is a route the optimizer
-- silently cannot use, which is worth remembering when sites are added.
-- --------------------------------------------------------------------
INSERT INTO building_route (from_building_id, to_building_id, distance_miles, fixed_dispatch_cost, cost_per_unit_mile) VALUES
  (1, 2, 9.20, 71.04, 0.0500),                -- Salina North -> Salina South
  (1, 3, 24.60, 89.52, 0.0500),               -- Salina North -> Abilene
  (1, 4, 96.40, 175.68, 0.0500),              -- Salina North -> Hays
  (1, 5, 88.70, 166.44, 0.0500),              -- Salina North -> Great Bend
  (2, 1, 9.20, 71.04, 0.0500),                -- Salina South -> Salina North
  (2, 3, 27.10, 92.52, 0.0500),               -- Salina South -> Abilene
  (2, 4, 94.00, 172.80, 0.0500),              -- Salina South -> Hays
  (2, 5, 86.20, 163.44, 0.0500),              -- Salina South -> Great Bend
  (3, 1, 24.60, 89.52, 0.0500),               -- Abilene -> Salina North
  (3, 2, 27.10, 92.52, 0.0500),               -- Abilene -> Salina South
  (3, 4, 118.50, 202.20, 0.0500),             -- Abilene -> Hays
  (3, 5, 110.30, 192.36, 0.0500),             -- Abilene -> Great Bend
  (4, 1, 96.40, 175.68, 0.0500),              -- Hays -> Salina North
  (4, 2, 94.00, 172.80, 0.0500),              -- Hays -> Salina South
  (4, 3, 118.50, 202.20, 0.0500),             -- Hays -> Abilene
  (4, 5, 58.90, 130.68, 0.0500),              -- Hays -> Great Bend
  (5, 1, 88.70, 166.44, 0.0500),              -- Great Bend -> Salina North
  (5, 2, 86.20, 163.44, 0.0500),              -- Great Bend -> Salina South
  (5, 3, 110.30, 192.36, 0.0500),             -- Great Bend -> Abilene
  (5, 4, 58.90, 130.68, 0.0500);              -- Great Bend -> Hays

-- --------------------------------------------------------------------
-- Movement history
-- --------------------------------------------------------------------
-- Initial placement for every item currently in a storage unit.
INSERT INTO item_movement (item_id, from_storage_id, to_storage_id)
SELECT item_id, NULL, storage_id FROM item WHERE storage_id IS NOT NULL;

-- A completed transfer: Tear-off Shovel #1 moved from the Salina North
-- locker (storage 1) to the shelf (storage 2) three weeks ago.
INSERT INTO item_movement (item_id, from_storage_id, to_storage_id, moved_at)
SELECT item_id, 1, 2, NOW() - INTERVAL 21 DAY
  FROM item WHERE item_name = 'Tear-off Shovel #1';

-- The in-transit compressor departed Salina North four hours ago.
-- to_storage_id is NULL because v2/v3 has nowhere to record a destination;
-- see the open issue on in-transit destinations.
INSERT INTO item_movement (item_id, from_storage_id, to_storage_id)
SELECT item_id, 1, NULL FROM item WHERE item_name = 'Air Compressor #99';

-- --------------------------------------------------------------------
-- Verification
-- --------------------------------------------------------------------

-- The optimizer's input. shortage_qty is d_jk, shippable_surplus_qty is s_ik.
-- Salina North / Nail Gun should read target 3, present 7, available 3:
-- a surplus of 4 of which only 3 can actually be loaded onto a truck.
SELECT b.city, b.street_address, it.name AS item_type,
       p.target_qty, p.present_qty, p.available_qty,
       p.shortage_qty, p.shippable_surplus_qty
  FROM v_building_item_type_position p
  JOIN building  b  ON b.building_id  = p.building_id
  JOIN item_type it ON it.item_type_id = p.item_type_id
 WHERE p.shortage_qty > 0 OR p.shippable_surplus_qty > 0
 ORDER BY p.building_id, p.item_type_id;

-- Totals per type. Hard hats should come back 7 shippable / 7 short.
SELECT it.name, SUM(p.shippable_surplus_qty) AS total_shippable,
       SUM(p.shortage_qty) AS total_short
  FROM v_building_item_type_position p
  JOIN item_type it ON it.item_type_id = p.item_type_id
 GROUP BY it.name ORDER BY it.name;

-- The in-transit compressor must appear in no building count. There are 7
-- rows in item of type 2, but the sum below must be 6 - Air Compressor #99
-- belongs to no building while it is in transit.
SELECT SUM(c.present_qty) AS compressors_counted
  FROM v_building_item_type_counts c
 WHERE c.item_type_id = 2;

-- --------------------------------------------------------------------
-- Expected optimizer results (exact MILP solve, HiGHS)
--
-- Regression targets for the solver.
--
-- OPTIMAL                                                  $575.44, 3 trips
--   Abilene      -> Salina South   1 compressor, 2 harnesses
--   Salina North -> Great Bend     1 nail gun, 1 ladder, 2 hard hats, 1 harness
--   Salina North -> Hays           2 nail guns, 1 compressor, 3 hard hats, 2 shovels
--   acquire at Abilene             2 hard hats  ($76.00)
--
-- NEAREST-SOURCE-FIRST BASELINE                          $1,072.19, 7 trips
--   46.3% worse. Opens Abilene->Hays and Hays->Great Bend for one item each,
--   and splits Hays's nail guns across two origins.
--
-- STRICT, all replacement_cost set to NULL                  $591.42, 4 trips
--   Opens a fourth trip, Salina North -> Abilene, carrying nothing but two
--   hard hats: $89.52 dispatch + $2.46 handling to deliver $76.00 of gear.
--   This is the recommendation replacement_cost exists to avoid.
--
-- MARGINAL COST PER SHORTAGE FILLED
--   Salina South / compressor   $24.62      Hays / compressor  $28.98
--   Salina South / harness       $1.36      Hays / nail gun     $4.82
--   Great Bend  / any item       $4.44      Hays / hard hat     $4.82
--   Abilene     / hard hat      $38.00  <- at the margin, this is the purchase
--   Most marginals are tiny because the trip is already being made. That is
--   the free-rider effect the fixed dispatch charge creates.
-- --------------------------------------------------------------------
