# Database Setup

Everyone runs their own local MySQL instance — we are not hosting a shared DB (see team discussion). Follow whichever section matches your OS to get `inventory_management` running locally.

## 1. Install MySQL Server

You need the actual **MySQL Server**, not just MySQL Workbench (Workbench is just the GUI client — it doesn't include a server).

**Windows (winget):**
```powershell
winget install --id Oracle.MySQL -e
```

**Windows (installer, if winget isn't available):**
Download the MySQL Installer from https://dev.mysql.com/downloads/installer/ and choose "MySQL Server" during setup. Follow its configuration wizard and set a root password when prompted (skip ahead to step 3 once installed — the installer's wizard handles initialization/service setup for you).

**Mac:**
```bash
brew install mysql
brew services start mysql
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt install mysql-server
sudo systemctl start mysql
```

## 2. Initialize and start the server (Windows manual/winget install only)

If you installed via winget or the raw MSI (no configuration wizard), you need to initialize the data directory and start the server yourself:

```powershell
$mysqld = "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe"
$datadir = "C:\ProgramData\MySQL\MySQL Server 8.4\Data"
New-Item -ItemType Directory -Force -Path $datadir

# Creates the data dir with root having NO password (fine for local dev only)
& $mysqld --initialize-insecure --datadir="$datadir"

# Starts the server in the foreground - leave this running in its own terminal
& $mysqld --datadir="$datadir"
```

Note: this runs MySQL as a plain process, not a Windows service, since installing a service requires admin rights. You'll need to re-run the last command (start) each time you want the DB available; the `--initialize-insecure` step only needs to happen once.

If you'd rather have it run automatically as a service and don't mind using an elevated terminal, run PowerShell as Administrator and use `& $mysqld --install` followed by `Start-Service MySQL84` instead of the manual start above.

## 3. Create the database

From the `Schema_versions` folder, using the `mysql` CLI (adjust `-u root -p` if you set a password):

```bash
mysql -u root < schema_v4.sql
mysql -u root < seed_data_v4.sql
```

Or in MySQL Workbench: open each file (schema_v4.sql first, then seed_data_v4.sql) and run it (the lightning-bolt "Execute" button) against your local connection.

Note: `schema_v4.sql` relies on `CHECK` constraints being enforced, which requires **MySQL 8.0.16 or later** (earlier versions parse them but silently ignore them). Run `mysql --version` to confirm before you start — the local MySQL 8.4 installs the team has been using are fine.

## 4. Verify

`seed_data_v4.sql` ends with a few `SELECT`s, including a surplus/shortage report comparing on-hand inventory to each building's target quantity, plus the exact optimizer results (optimal vs. naive-baseline cost) for the seeded 5-site scenario. If those return rows without errors, you're set up correctly.

## Files

- `schema_v4.sql` — current schema (table/view/index definitions only, no data). Fixes a v3 bug where a building/item-type combination with real stock but no `target_quantity` row was silently excluded from the optimizer's view entirely, instead of being reported as zero surplus. Also adds `CHECK` constraints on `replacement_cost`, `fixed_dispatch_cost`, and `cost_per_unit_mile`/`distance_miles` so a zero or negative value can't quietly corrupt the optimizer's cost comparisons. No new tables — see the file's header comment for details.
- `seed_data_v4.sql` — sample data modeling a five-site roofing company, sized to give the optimizer non-trivial work (includes the expected optimal-vs-naive cost comparison). Note: this seed data sets a target for every (building, item type) pair, so it doesn't exercise the v4 bug fix directly — see the schema file's comment.
- `schema_v3.sql` / `seed_data_v3.sql` — superseded by v4, kept for reference. Added `replacement_cost` to `item_type`, a generated `handling_cost_per_unit` on `building_route`, and split on-hand quantity into `present_qty`/`available_qty`.
- `schema_v2.sql` / `seed_data_v2.sql` — superseded by v3, kept for reference. Fixed v1's `BUILDING` FK bug and denormalized columns; introduced `item_type`, `target_quantity`, `item_movement`, and `building_route`.
- `initial_db_creation_v1.sql` — original v1, kept for reference.
