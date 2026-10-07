# Stock Daddy

Multi-site inventory management and redistribution system.
Group 1 · CSCI 841 Advanced Software Engineering · Fort Hays State University

Stock Daddy tracks equipment across an owner's businesses, buildings, rooms,
and storage units, compares what each building has against its stock
targets, and plans the cheapest way to move surplus items to where they're
short.

| Area | Owner | Folder |
|---|---|---|
| Frontend (pages, forms, routes) | Cody Hinz | `frontend/` |
| CRUD API | Benjamin Parks | `stock_daddy_api/` |
| Redistribution optimizer | Scott Thuong | `Optimizer/` |
| Database schema and seed data | Ivan Velo Castaneda | `Schema_versions/` |

---

## Running it

You need **Python 3.13** (check with `py --version` on Windows or
`python3 --version` on Mac/Linux). If it's missing, install it from
https://www.python.org/downloads/ and check **"Add Python to PATH"**.

> **Windows:** use `py` where these steps say `python`. If activating the
> virtual environment gives a security error in PowerShell, run
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` first.

### 1. Clone and set up (once)

```
git clone https://github.com/BaPark-FHSU-ASE/Group_1_Advanced_Software_Engineering_Proj.git
cd Group_1_Advanced_Software_Engineering_Proj
```

Create one virtual environment at the repo root and install everything into it:

**Windows**
```
py -m venv venv
venv\Scripts\activate
pip install -r frontend/requirements.txt -r stock_daddy_api/requirements.txt
```

**Mac/Linux**
```
python3 -m venv venv
source venv/bin/activate
pip install -r frontend/requirements.txt -r stock_daddy_api/requirements.txt
```

There's no database setup step. `frontend/stockdaddy.db` (SQLite) is
committed with the seed data already loaded.

### 2. Run it

```
cd frontend
python app.py
```

This one command starts both servers: the frontend on port 5000 and the
Stock Daddy API on port 5001. Stopping it with `Ctrl + C` stops both.

If you'd rather run the API on its own (e.g. to call it directly), start it
first with `cd stock_daddy_api` and `python app.py`; the frontend will see
it's already running and use it.

### 3. Open the app

Go to **http://127.0.0.1:5000** and log in with the seeded account:

- Email: `dale@prairieroofing.example`
- Password: `roofing123`

Or click **Register** to make your own account. Passwords are hashed, and
each owner only sees their own data.

### Settings (optional)

Defaults work out of the box. To change them, set environment variables in
your terminal before running. The API also reads `stock_daddy_api/.env`
(git-ignored), but the frontend doesn't, so put a setting there only if it's
for the API alone.

| Variable | Used by | Default |
|---|---|---|
| `DB_PATH` | frontend and API | `frontend/stockdaddy.db` |
| `API_PORT` | API | `5001` |
| `FLASK_DEBUG` | API | `True` |
| `STOCKDADDY_API_URL` | frontend | `http://127.0.0.1:5001` |
| `STOCKDADDY_START_API` | frontend | start the API automatically; set to `0` to turn off |

---

## Pages

| URL | Page | Purpose |
|---|---|---|
| `/dashboard` | Dashboard | Business → Building → Room → Storage hierarchy; add businesses and buildings |
| `/building/<id>` | Building | Rooms, storage units, stock levels, and setting stock targets |
| `/items` | Items | Every item and its status across all sites |
| `/items/new` | Add items | Add one item or several of the same type at once |
| `/items/<id>` | Item detail | Status, location, status changes, and full movement history |
| `/compliance` | Surplus & Shortage | On-hand vs. targets across all buildings |
| `/redistribute` | Redistribute | Runs the optimizer on live inventory: trips, items to buy new, and savings vs. the nearest-site baseline |

---

## API

A Flask API in model / repository / controller layers (`stock_daddy_api/app/`).
Requests and responses are JSON.

Each of these supports `GET` (list) and `POST` (create) on the collection,
and `GET`, `PUT`, and `DELETE` on `/<resource>/<id>`:

`/owners` · `/businesses` · `/buildings` · `/rooms` · `/storages` · `/item_types` · `/items`

Target quantities (REQ-15):

| Method | Path | Notes |
|---|---|---|
| `GET` | `/target_quantities` | Optional `?building_id=` filter |
| `GET` | `/target_quantities/<id>` | |
| `PUT` | `/target_quantities/<building_id>/<item_type_id>` | Body `{"owner_id": 1, "target_qty": 5}`. 201 if new, 200 if updated, never a duplicate row. 404 if the building isn't that owner's or the item type doesn't exist; 400 if `target_qty` isn't a whole number 0 or more. |
| `DELETE` | `/target_quantities/<id>` | |

Quick check with the API running: http://127.0.0.1:5001/businesses

---

## Database

**Engine: SQLite.** Switched from MySQL on 8/26 so there's no server to
install; `sqlite3` ships with Python, and the committed `.db` file means a
fresh clone works immediately.

**Changing the schema or seed data:** edit `Schema_versions/schema_v6.sql` or
`seed_data_v6.sql`, then rebuild and commit the database alongside your change:

```
python Schema_versions/build_db.py
```

This drops and recreates `frontend/stockdaddy.db` from scratch. The apps read
that file directly, so a schema change nobody rebuilds has no effect for
anyone else.

**Looking at the data:** `sqlite3 frontend/stockdaddy.db` (or
`python -m sqlite3`), or open the file in DB Browser for SQLite, TablePlus,
or VS Code's SQLite extension.

```
sqlite> SELECT * FROM v_building_item_type_position LIMIT 5;
```

**Schema files** in `Schema_versions/`:

- `schema_v6.sql` / `seed_data_v6.sql`: current. v6 adds
  `item_movement.from_status` / `to_status` so a status change with no
  location change is recorded (REQ-11), and `item_type.service_life_days`
  for item aging (REQ-23). The seed data is a five-site roofing company.
- `build_db.py`: rebuilds `frontend/stockdaddy.db` from the two files above.
- `schema_v5.sql` / `seed_data_v5.sql`: superseded; added login columns and
  ported the schema from MySQL to SQLite.
- v4 and earlier: MySQL dialect, kept for history. Each file's header
  explains what changed at that step.
- `ERD_v3.mmd`: entity-relationship diagram (Mermaid).

---

## Optimizer

`Optimizer/` plans inter-building redistribution as a fixed-charge
transportation problem. `branch_and_bound.py` finds the optimal plan (using
numpy/scipy for its LP relaxations), `nearest_source.py` is the
nearest-site baseline it's compared against, and `enumerate_bruteforce.py`
checks optimality on small instances. The `/redistribute` page calls it
through `frontend/redistribution.py`.

---

## Tests

Each suite runs against a temporary copy of the database, so the committed
`stockdaddy.db` never changes.

| Suite | Run from | Command |
|---|---|---|
| Frontend | `frontend/` | `python tests/run_all_tests.py` |
| API | `stock_daddy_api/` | `python tests/run_all_tests.py` |
| Optimizer | repo root | `python Optimizer/tests/run_all_tests.py` |

`frontend/tests/test_targets.py` and `test_api_launcher.py` include tests
that start the real API on a free port; they're skipped if the API's
requirements aren't installed.

---

## Repository layout

```
├── frontend/              Flask app: pages, forms, routes
│   ├── app.py             routes
│   ├── db.py              database queries used by the pages
│   ├── api_client.py      calls to the Stock Daddy API
│   ├── api_launcher.py    starts the API when the frontend starts
│   ├── redistribution.py  database → optimizer → /redistribute page
│   ├── stockdaddy.db      the database (SQLite, committed, seeded)
│   ├── templates/         Jinja2 pages; all extend base.html
│   ├── static/            CSS, JS, favicon
│   └── tests/
├── stock_daddy_api/       Flask JSON API
│   ├── app.py             starts the API
│   ├── app/models/        one class per table
│   ├── app/repositories/  SQL for each table
│   ├── app/controllers/   routes
│   └── tests/
├── Optimizer/             redistribution solver and its tests
└── Schema_versions/       schema, seed data, ERD, build_db.py
```
