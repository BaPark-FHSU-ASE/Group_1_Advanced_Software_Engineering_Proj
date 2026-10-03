# Stock Daddy — Frontend

Multi-Site Inventory Management & Redistribution System
Group 1 · FHSU Advanced Software Engineering

---

## How to run this on your machine

### Step 1 — Make sure Python is installed

Open a terminal and run:

```
py --version
```

You should see something like `Python 3.13.x`. If you get an error, download Python from https://www.python.org/downloads/ — during install, check **"Add Python to PATH"**.

> **Windows note:** Use `py` instead of `python`. If `venv\Scripts\activate` gives a security error in PowerShell, run this first:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

---

### Step 2 — Clone the repo (if you haven't already)

```
git clone https://github.com/BaPark-FHSU-ASE/Group_1_Advanced_Software_Engineering_Proj.git
cd Group_1_Advanced_Software_Engineering_Proj
```

---

### Step 3 — Navigate into the frontend folder

```
cd frontend
```

---

### Step 4 — Create a virtual environment

**Windows:**
```
py -m venv venv
venv\Scripts\activate
```

**Mac/Linux:**
```
python3 -m venv venv
source venv/bin/activate
```

You'll know it worked when you see `(venv)` at the start of your terminal line.

---

### Step 5 — Install dependencies

```
pip install -r requirements.txt
```

That's it for setup — there's no separate database step. `stockdaddy.db`
(SQLite) is already in this folder, committed to the repo with the seed
data loaded. Nothing to install, no server to start, no credentials to set.

---

### Step 6 — Run the app

**Windows:**
```
py app.py
```

**Mac/Linux:**
```
python3 app.py
```

---

### Step 7 — Open in your browser

Go to: **http://127.0.0.1:5000**

Log in with the seeded test account:
- Email: `dale@prairieroofing.example`
- Password: `roofing123`

Or click **Register** to create your own account — auth is real now (hashed
passwords, checked against the database), not a hardcoded stub.

To stop the app, press `Ctrl + C` in the terminal.

---

## Pages

| URL | Page | Purpose |
|---|---|---|
| `/dashboard` | Dashboard | Full hierarchy: Business → Building → Room → Storage |
| `/building/<id>` | Building detail | Rooms, storage units, and stock level snapshot |
| `/items` | Items | All items with status across every site |
| `/items/<id>` | Item detail | Status, location, and full movement history |
| `/compliance` | Surplus & Shortage | Compare on-hand vs targets across all buildings |
| `/redistribute` | Redistribute | Runs Scott's optimizer on live inventory: optimal trips, buy-new items, and savings vs. the nearest-site baseline |

---

## Project structure

```
frontend/
├── app.py                  — Flask routes, all querying the real DB
├── db.py                   — SQLite connection layer + all queries
├── redistribution.py       — DB → Optimizer → page bridge for /redistribute
├── stockdaddy.db           — the actual database (SQLite, committed, pre-seeded)
├── requirements.txt        — Python dependencies (Flask, plus numpy/scipy for the optimizer)
├── .gitignore
├── README.md
├── templates/
│   ├── base.html           — Shared layout, favicon, CSS link
│   ├── nav.html            — Sidebar navigation
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── building.html
│   ├── items.html
│   ├── item_detail.html
│   ├── compliance.html
│   └── redistribute.html
└── static/
    ├── favicon.ico
    ├── css/main.css
    └── js/main.js
```

If you edit the schema (`Schema_versions/schema_v5.sql`) or the seed data,
regenerate `stockdaddy.db` with `python Schema_versions/build_db.py` and
commit the result — the app reads that file directly, nothing rebuilds it
automatically.

---

## Notes for teammates

**Benjamin (CRUD API):** All routes now query the real DB via `db.py` — no more `# TODO`/placeholder dicts to replace.

**Ivan (Database):** Schema is SQLite now (`Schema_versions/schema_v5.sql`), not MySQL. Registration/login use hashed passwords (werkzeug), never plaintext. `db.py` has the full query layer.

**Scott (Optimizer):** `/redistribute` is wired to your engine. Clicking **Run Optimizer** POSTs to the route, which calls `redistribution.generate_plan(owner_id)`: `db.get_optimizer_inputs()` reads buildings, item types, `building_route`, and supply/demand from `v_building_item_type_position`; `build_instance()` turns that into an `Instance` (buildings and types keyed by database id as strings); then `branch_and_bound()` (10 s deadline, gap shown if it isn't proven optimal) and `nearest_source_first()` (baseline) run, and `to_view()` maps the `Plan` back to display names. The optimizer package itself is unchanged. Seed data is your instance B, so `tests/test_redistribute.py` checks the live page reproduces $575.44 / $1072.19. Costs still come from SQLite REAL columns, so compare with a tolerance.
