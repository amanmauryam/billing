# Offline Shop POS

A local, offline-first point-of-sale system for a small retail shop on one
Windows computer. It manages products and stock, scans barcodes, completes
GST-aware bills, saves and reprints receipts, shows real dashboard metrics,
and backs up/restores the local database.

- **Backend:** Django + SQLite
- **Frontend:** Django templates + locally compiled Tailwind CSS + vanilla JS
- **Printing:** browser-native printing for 58mm and 80mm receipts
- **Runs at:** `http://127.0.0.1:8000`
- **Currency:** INR (₹)

See [`design.md`](design.md) for the full product and engineering specification.

---

## 1. Requirements

- Windows 10/11
- Python 3.12 or newer (works with 3.14)
- Node.js 18+ (only needed to rebuild the Tailwind CSS)

The repository already contains a pre-built `static/css/output.css`, so the
application runs offline without Node.js once dependencies are installed.

---

## 2. First-time setup (Windows PowerShell)

All commands are assumed to run from this folder (the folder containing
`manage.py`, `requirements.txt`, and `design.md`).

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# If activation is blocked, allow it for the current session:
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 2. Install Python dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 3. Apply database migrations (creates db.sqlite3)
python manage.py migrate

# 4. Build the local Tailwind CSS (only if you changed templates/static)
npm install
npm run build:css

# 5. Start the local server, bound to loopback only
python manage.py runserver 127.0.0.1:8000
```

Then open `http://127.0.0.1:8000` in your browser. On first launch you will be
taken to the **Shop setup** screen (shop name, receipt width, GST pricing mode,
low-stock threshold, receipt footer). Finish setup, add products, and start
billing.

> To use the optional Django admin for low-level inspection, create a staff
> user with `python manage.py createsuperuser` and visit `/admin/`. Admin is
> for local maintenance only.

---

## 3. Everyday use

**Easiest option (Windows):** double-click `start.bat` in the project root
(the folder that contains `.venv` and `main`). It starts the server and opens
the browser automatically. Keep the black window open while billing; close it
to stop. Right-click `start.bat` → **Send to → Desktop (create shortcut)** to
put it on the desktop.

**Or run it manually:**

```powershell
# From the project folder, with the virtual environment active:
.\.venv\Scripts\Activate.ps1
python manage.py runserver 127.0.0.1:8000
```

- **POS / New Bill** — the scan/search field is focused automatically. Scan a
  barcode (a keyboard-wedge scanner types the code and usually sends Enter) or
  type to search. Exact barcode matches add one unit.
- **Products** — add/edit/deactivate products, adjust stock (every change is
  recorded in the stock history).
- **Sales** — search bills by number or date and reprint a saved receipt.
  Reprinting never changes stock or creates a new bill.
- **Settings** — shop details, receipt width, pricing mode, low-stock
  threshold, footer.
- **Backup & Restore** — create and restore SQLite backups.

All data is stored on this computer only. The header shows a static
"Stored on this computer" label; there is no cloud sync or internet dependency.

### GST pricing mode

- **GST-inclusive:** the selling price already includes GST.
- **GST-exclusive:** GST is added on top of the selling price.

The mode affects **future** bills only. Existing receipts keep the amounts that
were saved when the sale was made. This software performs calculations; it does
not guarantee statutory tax compliance — confirm invoicing requirements with a
professional.

---

## 4. Receipts and printing

Open a saved sale and click **Print receipt**. The receipt renders from saved
snapshots, so it stays accurate even after products are renamed or repriced.

- 58mm and 80mm widths are supported (set in Settings).
- The browser print dialog and printer driver control margins, scaling, and
  cut behaviour; configure your thermal printer once in Windows.
- Silent printing is not guaranteed by browser printing.

---

## 5. Backups and restore

- Backups are written to the `backups` folder next to this project folder by
  default (override with the `DJANGO_BACKUP_DIR` environment variable).
- Backups use SQLite's online backup API, so a consistent snapshot is taken
  even while the app is running.
- Restore first validates the chosen file, then saves a safety backup of the
  current database before replacing it.
- A backup on the same computer does not protect against theft or disk failure.
  Copy backups to an external drive periodically.

To restore into a scratch copy for testing without touching live data:

```powershell
python manage.py test apps.core.tests.BackupServiceTests
```

---

## 6. Configuration (environment variables)

Machine-specific settings and secrets live in environment variables, not in
source control. Set them before starting the server.

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | local dev key | Change for any non-local deployment |
| `DJANGO_DEBUG` | `true` | Set to `false` for production-style use |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma-separated allowed hosts |
| `DJANGO_DB_NAME` | `db.sqlite3` | SQLite database file path |
| `DJANGO_BACKUP_DIR` | `..\backups` | Backup directory |

Example:

```powershell
$env:DJANGO_DEBUG = "false"
$env:DJANGO_SECRET_KEY = "replace-with-a-long-random-value"
python manage.py runserver 127.0.0.1:8000
```

---

## 7. Running the tests

```powershell
python manage.py test
```

The suite covers product validation and stock movements, GST-inclusive and
GST-exclusive calculations, rounding, atomic checkout and rollback, duplicate
checkout tokens, inactive products, sale snapshots, receipts/reprints, the
dashboard, and backup/restore.

---

## 8. Project structure

```text
main/
├── config/              # Django project settings and root URLs
├── apps/
│   ├── core/            # ShopSettings, dashboard, setup, backup/restore
│   ├── products/        # Product catalogue and stock movements view
│   └── billing/         # Sales, sale items, stock movements, checkout service
├── templates/           # base shell, dashboard, products, pos, sales, receipts
├── static/
│   ├── css/input.css    # Tailwind source (design tokens + components)
│   ├── css/output.css   # locally compiled CSS (committed for offline use)
│   ├── js/pos.js        # scanner + cart interaction
│   ├── icons/           # bundled Lucide SVGs (committed; served locally)
│   └── fonts/           # bundled Inter woff2 files (committed; served locally)
├── manage.py
├── requirements.txt
├── package.json         # Tailwind build scripts + dev-only asset sources
└── design.md
```

The Lucide icons and the Inter font are copied into `static/` from the
dev-only npm packages (`lucide-static`, `@fontsource-variable/inter`) and are
committed, so no internet or extra build step is needed at runtime.

---

## 9. Troubleshooting

**PowerShell blocks `Activate.ps1`** → run
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate
again.

**`npm` script blocked ("running scripts is disabled")** → call
`npm.cmd run build:css`, or fix the execution policy as above.

**Scanner adds nothing / adds a stray character** → make sure the POS scan
field is focused. Configure the scanner to send an Enter (CR) suffix. Barcodes
are matched exactly and case-insensitively.

**"Only N left in stock" or checkout fails** → stock changed since the cart was
built; the server is the source of truth. Reload the cart and retry.

**Database is busy** → SQLite handles one local till well. Keep another app
from holding the file, and avoid running two servers against the same file.

**CSS looks unstyled** → rebuild with `npm run build:css`, or confirm
`static/css/output.css` exists.

**After a restore, restart the server** for a clean reload.

---

## 10. Known limitations (v1)

- Single computer, single till. Not designed for concurrent multi-machine
  checkout (that requires a tested PostgreSQL deployment).
- No cloud sync, e-commerce, payment gateway, loyalty, or accounting modules.
- Browser-native printing only; silent printing is not guaranteed.
- GST calculations only; CGST/SGST/IGST splitting is not implemented until the
  shop's jurisdiction and transaction rules are configured and tested.
- No refund/void workflow yet. Sales are immutable; refunds would need an
  audited reversal workflow rather than deletion.
