# What the frontend expects from the API

The frontend talks to the database only through `stock_daddy_api/`, by way
of `frontend/api_client.py`. This file lists every endpoint the frontend
calls and the shape it expects back.

Endpoints marked **NEW** didn't exist when this was written (Nov 23). They
are the frontend's half of the V2 checklist. Build them to this shape and
the pages work without changes. If a shape needs to change, change it here
and in `api_client.py` in the same PR.

## Conventions (same as the existing endpoints)

- The caller says who they are with `user_id`: a query parameter on GET and
  DELETE, a body field on POST and PUT.
- Errors come back as `{"error": "plain sentence"}`. The frontend shows that
  sentence to the user as-is, so write it for a person, not a developer.
- 400 bad input, 403 wrong role, 404 not found *or not yours* (never tell
  the two apart, NF-REQ-12), 409 conflict (still has things inside, email
  taken, infeasible plan).
- Lists and reports leave out anything retired.
- "Member" means any row in `business_member` (owner or employee). Every
  read below returns only what the user is a member of.

## Auth (NEW)

| Call | Body | Returns |
|---|---|---|
| `POST /auth/register` | `first_name, last_name, email, password` | 201 owner (below). 409 if the email is taken. 400 if the password is under 8 characters. The API hashes the password; nobody sends a hash. |
| `POST /auth/login` | `email, password` | 200 owner. 401 `Invalid email or password.` |

Owner: `{owner_id, first_name, last_name, email, memberships: [{business_id, role}]}`.
`memberships` is empty for a new account.

`POST /owners` should stop taking `password_hash` once these exist.

## Reports (NEW, read-only, `?user_id=`)

These are Ivan's queries from the old `frontend/db.py`, moved into API
repositories. The shapes are the ones `db.py` returned, plus the fields
marked *added*.

### `GET /reports/dashboard`

```
[{id, name, role*,
  buildings: [{id, name, address, street_address*, city*, state*,
               room_count, storage_count, item_count, shortage_count,
               rooms: [{id, name, storages: [{id, name, type, item_count}]}]}]}]
```

`role` is the user's role in that business (`owner` / `employee`).

### `GET /reports/buildings/<building_id>`

```
{id, name, address, street_address*, city*, state*, business_id*, role*,
 rooms: [{id, name, storages: [{id, name, type, item_count}]}],
 compliance: [{item_type_id*, item_type, target, on_hand, available, variance}]}
```

404 if the user isn't a member of the building's business.

### `GET /reports/storages/<storage_id>` (UI-REQ-2)

```
{id, type, role, room: {id, name}, building: {id, name},
 items: [{id, name, type, status, expired}]}
```

### `GET /reports/items`

```
[{id, name, type, status, building, room, storage, expired*}]
```

`expired` is true when the item is past its type's service life (REQ-23).

### `GET /reports/items/<item_id>`

```
{id, name, type, item_type_id*, status, building, room, storage,
 storage_id, date_added, role*, expired*, days_over*,
 movement_history: [{date, from, to, status_change}]}
```

`days_over` is null unless `expired`.

### `GET /reports/compliance`

```
[{building_id*, building, item_type_id*, item_type, target, on_hand, available, variance}]
```

### `GET /reports/expired_items` (REQ-23)

```
[{id, name, type, status, age_days, service_life_days, days_over}]
```

### `GET /reports/storage_choices`

```
[{id, building, label}]
```

Every non-retired storage unit the user can put items in.

## Businesses, buildings, rooms, storage (exist)

| Call | Body |
|---|---|
| `POST /businesses` | `name, owner_id` (the user; they become its owner) |
| `PUT /businesses/<id>` | `user_id, name` |
| `POST /businesses/<id>/retire` | `user_id` |
| `POST /buildings` | `user_id, business_id, street_address, city, state` |
| `PUT /buildings/<id>` | `user_id, business_id, street_address, city, state` |
| `POST /buildings/<id>/retire` | `user_id` |
| `POST /rooms` | `user_id, building_id, location` |
| `PUT /rooms/<id>` | `user_id, building_id, location` |
| `POST /rooms/<id>/retire` | `user_id` |
| `POST /storages` | `user_id, room_id, storage_type` |
| `PUT /storages/<id>` | `user_id, room_id, storage_type` |
| `POST /storages/<id>/retire` | `user_id` |

Retire answers 409 with a sentence like `Can't retire this room: 2 storage
units and 21 items still inside`, which the page shows as-is.

## Items

| Call | Body | Returns |
|---|---|---|
| `POST /items/bulk` **NEW** (REQ-14) | `user_id, storage_id, item_type_id, quantity (1-100), item_name?` | 201 `{item_ids: [...]}`. Port `db.add_items`: same naming rules, one movement row per item, one transaction. |
| `POST /items/<id>/status` **NEW** (REQ-11, REQ-12) | `user_id, status, storage_id?` | 200 `{changed: bool}`. Port `db.update_item_status`: the item update and its movement row in one transaction. `storage_id` is required when leaving In Transit (400 `Choose where the item arrived.`). Employees can do this. |
| `PUT /items/<id>` (exists) | `user_id, item_type_id, storage_id, item_status, item_name?` | The frontend only uses it to rename or retype an item, and sends the item's current storage and status unchanged. Moves go through `/status`. |
| `POST /items/<id>/retire` (exists) | `user_id` | |

`DELETE /items/<id>` is never called.

## Item types (exist, REQ-9)

| Call | Body |
|---|---|
| `GET /item_types?user_id=` | |
| `POST /item_types` | `user_id, name, description?, replacement_cost?, service_life_days?` |
| `PUT /item_types/<id>` | same as POST |
| `DELETE /item_types/<id>?user_id=` | |

**NEW:** accept and return `service_life_days` (REQ-23). Today the API
ignores it.

## Stock targets (exists, REQ-15)

`PUT /target_quantities/<building_id>/<item_type_id>` with `owner_id,
target_qty`. The frontend also sends `user_id` (same value) so the endpoint
can move to `require_role` without a frontend change.

## Team (exists)

| Call | Body |
|---|---|
| `GET /businesses/<id>/members?user_id=` | |
| `POST /businesses/<id>/members` | `user_id, email, role` |
| `PUT /businesses/<id>/members/<member_id>` | `user_id, role` |
| `DELETE /businesses/<id>/members/<member_id>?user_id=` | |

**NEW:** include `first_name, last_name, email` on each member so the team
page can show names. Without them it falls back to "Account #id".

## Route costs (NEW, REQ-17)

| Call | Body | Returns |
|---|---|---|
| `GET /routes?user_id=` | | `[{route_id, from_building_id, from_label, to_building_id, to_label, distance_miles, fixed_dispatch_cost, cost_per_unit_mile, handling_cost_per_unit}]` for routes whose two ends are both in the user's businesses |
| `POST /routes` | `user_id, from_building_id, to_building_id, distance_miles, fixed_dispatch_cost, cost_per_unit_mile` | 201 route. Owner of both buildings. |
| `PUT /routes/<id>` | `user_id, distance_miles, fixed_dispatch_cost, cost_per_unit_mile` | route |
| `DELETE /routes/<id>?user_id=` | | 204 |

Labels follow `db.get_optimizer_inputs`: the city, plus the street when the
user has two buildings in that city.

## Movement history (NEW, REQ-13)

`GET /movements?user_id=` with any of these optional filters:
`item_id, item_type_id, building_id, status, date_from, date_to`
(dates are `YYYY-MM-DD`, inclusive) and `q` (matches the item name).

```
[{movement_id, date, item_id, item_name, item_type, building, from, to, status_change}]
```

Newest first. `from`, `to` and `status_change` use the same text as an
item's movement history.

`GET /movements/export?user_id=&...` takes the same filters and returns
`text/csv` with a header row and the same columns.

## Redistribution plan (NEW, REQ-18 to REQ-21, REQ-24)

`POST /plans` with `user_id`. Owner only. Port Scott's adapter
`frontend/redistribution.py` and `db.get_optimizer_inputs` behind the API;
they read only non-retired items that aren't In Use. The frontend no longer
has the adapter; get it, and its tests in `frontend/tests/test_redistribute.py`
(the instance B checks), from commit `c3daefc`:

    git show c3daefc:frontend/redistribution.py
    git show c3daefc:frontend/tests/test_redistribute.py

Returns the dict `redistribution.generate_plan` returned, plus
`shortage_costs` for REQ-21:

```
{generated: true, no_shortages, optimal, gap,
 total_cost, transfer_cost, acquisition_cost, greedy_cost,
 trips: [{from, to, items: [{qty, type}], dispatch_cost, handling_cost}],
 acquisitions: [{building, type, qty, unit_cost, cost}],
 shortage_costs: [{building, type, qty, cost, cost_per_unit}]}
```

`shortage_costs` has one row per shortage the plan fills: what filling it
cost (its share of trip costs plus any purchases) and that divided by the
quantity.

409 with a sentence when no plan can cover every shortage.
