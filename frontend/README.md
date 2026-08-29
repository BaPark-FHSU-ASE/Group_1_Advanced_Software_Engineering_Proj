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
| `/redistribute` | Redistribute | Optimization plan output (Scott's engine plugs in here) |

---

## Project structure

```
frontend/
├── app.py                  — Flask routes, all querying the real DB
├── db.py                   — SQLite connection layer + all queries
├── stockdaddy.db           — the actual database (SQLite, committed, pre-seeded)
├── requirements.txt        — Python dependencies (just Flask)
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

**Scott (Optimizer):** The `/redistribute` route passes a `plan` dict to `redistribute.html`. Set `plan["generated"] = True` and populate `plan["trips"]`, `plan["total_cost"]`, and `plan["greedy_cost"]` from your engine output. Note: `building_route.handling_cost_per_unit` is stored as SQLite's floating-point REAL, not exact decimal — compare costs with a small tolerance, not exact equality.
