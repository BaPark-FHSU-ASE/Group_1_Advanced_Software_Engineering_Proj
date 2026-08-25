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
mysql -u root < schema_v2.sql
mysql -u root < seed_data_v2.sql
```

Or in MySQL Workbench: open each file (schema_v2.sql first, then seed_data_v2.sql) and run it (the lightning-bolt "Execute" button) against your local connection.

## 4. Verify

`seed_data_v2.sql` ends with a few `SELECT`s, including a surplus/shortage report comparing on-hand inventory to each building's target quantity. If those return rows without errors, you're set up correctly.

## Files

- `schema_v2.sql` — table/view definitions only (no data). Fixes v1's `BUILDING` FK bug and denormalized colu; adds `item_type`, `target_quantity`, and `item_movement` to support the transfer-optimization work.
- `seed_data_v2.sql` — sample data modeling a two-building roofing company scenario (see the "surplus/shortage" query at the bottom for what it demonstrates).
- `initial_db_creation_v1.sql` — original v1, kept for reference.
