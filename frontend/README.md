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

Login with:
- Username: `admin`
- Password: `admin`

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
stockdaddy/
├── app.py                  — Flask routes (all TODO markers for DB hookup)
├── requirements.txt        — Python dependencies (just Flask)
├── .gitignore
├── README.md
├── templates/
│   ├── base.html           — Shared layout, favicon, CSS link
│   ├── nav.html            — Sidebar navigation
│   ├── login.html
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

---

## Notes for teammates

**Benjamin (CRUD API):** Every route in `app.py` has a `# TODO` comment. Replace the placeholder dicts with real DB queries there.

**Ivan (Database):** The placeholder data in `app.py` mirrors the schema exactly — field names match the ERD.

**Scott (Optimizer):** The `/redistribute` route passes a `plan` dict to `redistribute.html`. Set `plan["generated"] = True` and populate `plan["trips"]`, `plan["total_cost"]`, and `plan["greedy_cost"]` from your engine output.
