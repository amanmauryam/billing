# Offline Shop POS System
## Production-Oriented Product & Engineering Specification

**Document type:** Product requirements + UX/UI + technical design  
**Product:** Offline Shop POS  
**Primary deployment:** One Windows computer, running locally at `http://127.0.0.1:8000`  
**Initial database:** SQLite  
**Backend:** Django  
**Frontend:** Django templates, locally compiled Tailwind CSS, and vanilla JavaScript  
**Printing:** Browser-native printing for 58mm and 80mm thermal receipts  
**Primary currency:** INR (₹)  
**Status:** Implementation specification

---

## 1. Product Vision

Build a reliable, simple point-of-sale application for small Indian retail shops. A shopkeeper must be able to manage products, scan barcodes, complete sales, maintain stock, review previous bills, and print receipts without an internet connection.

The product should feel like a dedicated retail application rather than a generic admin panel. Checkout speed, data integrity, readability, recoverability, and predictable behaviour are more important than decorative visuals.

### Product principles

1. **Offline by default:** All essential assets and workflows run locally.
2. **Fast checkout:** Barcode-first workflow, keyboard support, minimal clicks.
3. **Correct billing:** Server-side totals, explicit GST pricing mode, Decimal arithmetic.
4. **Safe stock:** A completed sale deducts inventory exactly once.
5. **Historical accuracy:** Old bills preserve the item name, price, and tax rate used at sale time.
6. **Recoverable data:** Backups and restore procedures are understandable and tested.
7. **Maintainable architecture:** Django ORM and migrations; avoid SQLite-specific business logic.
8. **Honest status:** Never show a sale, backup, or print operation as successful before it actually succeeds.

---

## 2. Scope

### Included in the initial release

- Local installation and first-run setup.
- Shop settings.
- Product create, edit, deactivate, search, and stock visibility.
- Optional unique product barcodes.
- Barcode scanner support for keyboard-wedge USB/Bluetooth scanners.
- POS cart, quantity editing, item removal, and live totals.
- GST-aware billing with configurable inclusive/exclusive selling prices.
- Atomic sale creation and stock deduction.
- Saved bills, bill details, and reprinting.
- Dashboard metrics and low-stock warnings.
- 58mm/80mm receipt templates.
- Database backup and safe restore workflow.
- Automated tests and a Windows PowerShell run guide.
- Offline operation after all dependencies are installed.

### Explicitly out of scope for v1

- Cloud accounts, remote synchronization, and multi-branch sync.
- Multi-counter concurrency across multiple computers.
- E-commerce and online payment gateway integrations.
- Automatic GST returns or claims of statutory compliance.
- Native silent printing without browser/printer configuration.
- Supplier purchase orders, customer loyalty, credit ledgers, or advanced accounting unless separately approved.

Do not add buttons for features that do not work. Hide deferred modules until implemented.

---

## 3. Users and Primary Journeys

### Primary user: shopkeeper

The user may have limited computer experience and needs clear labels, obvious actions, and useful error messages.

### Journey A: first launch

1. Start the local application.
2. Complete a short shop setup: shop name, optional contact/address, receipt width, pricing mode, and low-stock threshold.
3. Add the first product.
4. Open POS and make a test bill.
5. Print a test receipt and verify printer settings.

### Journey B: add inventory

1. Open Products.
2. Select Add Product.
3. Enter name, optional barcode, selling price, stock quantity, and GST rate.
4. Save and see a clear confirmation.
5. Find the product by name or barcode.

### Journey C: checkout

1. Open POS; scanner field is focused automatically.
2. Scan an item; a matching product is added to the cart.
3. Scan further items or change quantities.
4. Review subtotal, GST, and grand total.
5. Complete sale.
6. The server validates stock and prices, saves the sale atomically, and deducts stock once.
7. Open the saved receipt and print it.

### Journey D: reprint a bill

1. Open Sales.
2. Find a bill by bill number or date.
3. Open saved receipt.
4. Print again without creating a new sale or changing stock.

### Journey E: backup

1. Open Backup & Restore.
2. Create a backup.
3. See the exact saved file location and result.
4. Periodically test restore into a separate database before trusting the backup.

---

## 4. Product Requirements and Acceptance Criteria

### Product management

- Create, edit, search, and deactivate products.
- Required: name, selling price, stock quantity, GST percentage.
- Optional: barcode.
- Reject blank names, invalid or negative prices, negative stock, invalid GST values, and duplicate non-empty barcodes.
- Deactivated products cannot be added to new bills, but remain visible in historical receipts.
- Never delete historical sale records through product deletion.
- Support a configurable low-stock threshold.
- Use database constraints where appropriate, backed by server-side validation.

### POS

- Scanner input is visible and receives initial focus.
- Exact barcode match takes precedence over text search.
- A scanner suffix such as Enter can trigger a scan.
- Unknown barcodes show a clear message and do not silently add an item.
- Manual product search is available.
- Cart supports quantity increase/decrease, direct quantity edit, and item removal.
- Quantities must be positive and must not exceed available stock.
- Cart totals update immediately in the browser for responsiveness.
- The server independently recalculates all amounts during checkout.
- Disable the Complete Sale button while a request is in progress.
- Prevent duplicate sales caused by repeated clicks or retrying the same checkout request.
- A failed checkout must not create partial sale records or deduct stock.
- After success, show the saved bill number and receipt/print action.

### Sales history

- List bill number, date/time, total item quantity, and grand total.
- Search by bill number and filter by date.
- Show the exact saved item, quantity, unit price, GST rate, tax, and totals.
- Reprinting does not modify stock or create another bill.
- Historical records are immutable through normal product edits.

### Dashboard

- Today's sales and bill count are calculated from saved completed sales.
- Low-stock count is calculated from active inventory.
- Recent bills link to their saved receipt.
- Empty states explain what to do next.
- No hardcoded business metrics or fake chart data.

### Offline operation

- Essential CSS, JavaScript, fonts, and icons are served locally.
- No essential CDN, third-party API, remote font, or internet request.
- Product management, checkout, sales history, and receipt rendering work with the internet disconnected.
- The interface clearly communicates that records are stored on this computer.

---

## 5. UX and Visual Design

### Visual direction

A polished, restrained retail interface. It should look dependable and professional, with a high-contrast checkout workspace and little visual clutter.

### Design tokens

| Token | Value | Purpose |
|---|---|---|
| Primary | `#2563EB` | Main action and active navigation |
| Primary hover | `#1D4ED8` | Hover state |
| App background | `#F8FAFC` | Main canvas |
| Surface | `#FFFFFF` | Cards and panels |
| Main text | `#0F172A` | Headings and key figures |
| Secondary text | `#64748B` | Supporting labels |
| Border | `#E2E8F0` | Dividers and field borders |
| Success | `#15803D` | Saved/paid confirmation |
| Warning | `#B45309` | Low-stock and caution |
| Danger | `#B91C1C` | Errors and destructive actions |

### Typography and interaction

- Use a locally bundled font or system font stack such as `Inter, Arial, sans-serif`.
- Body text: 14–16px; page headings: 24–30px.
- Product names and total amounts must be readable at a glance.
- Controls should generally be at least 40–44px high.
- Use visible keyboard focus indicators.
- Do not use colour alone to communicate status.
- Use consistent spacing based on a 4px scale.
- Keep animations minimal and respect reduced-motion preferences where relevant.
- Use clear confirmation dialogs for destructive operations.

### Application shell

Desktop layout:

- Left sidebar with Dashboard, POS, Products, Sales, Settings, and Backup & Restore.
- Top bar with current page, local/offline indicator, and optional shop name.
- Main content with page title, brief helper text, and one obvious primary action.
- Responsive layout that remains usable on a tablet.

The local/offline indicator must not imply remote synchronization or internet monitoring. A static label such as “Stored on this computer” is preferable to a misleading live network status.

### Dashboard screen

- Greeting or page title.
- Primary “New Bill” action.
- Summary cards: today's sales, bills today, low-stock items.
- Recent bills list.
- Low-stock products list or link.
- Helpful empty states for a new installation.

### Products screen

- Search input supporting product name and barcode.
- Add Product action.
- Table columns: product, barcode, selling price, GST, stock, status, actions.
- Low stock and out-of-stock states.
- Edit and deactivate actions.
- Pagination for larger catalogues.
- Avoid loading every product into the browser at once.

### Product form

Fields:

- Product name (required).
- Barcode (optional).
- Selling price (required).
- GST rate (required).
- Opening/current stock quantity (required for creation).
- Active status (for editing).

Use labelled inputs, inline validation, appropriate numeric input modes, and server-rendered validation errors. Do not rely only on HTML/JavaScript validation.

### POS screen

Recommended desktop layout:

```text
┌──────────────────────────────────────────────────────────────────┐
│ POS / New Bill                     Stored on this computer        │
├──────────────────────────────────────────────────────────────────┤
│ [ Scan barcode or search by product name                     ]   │
├───────────────────────────────────┬──────────────────────────────┤
│ Product search/results             │ Current cart                 │
│                                   │ Product  Qty  Price  Amount  │
│ Compact rows or results            │ ...                          │
│                                   │                              │
│                                   │ Subtotal                      │
│                                   │ Taxable amount / GST          │
│                                   │ GRAND TOTAL                   │
│                                   │ [ Complete Sale ]             │
└───────────────────────────────────┴──────────────────────────────┘
```

POS interaction rules:

- Keep the scanner/search field easy to find.
- Focus it on initial page load.
- After a successful scan/add, return focus to it unless the user is actively editing another field.
- Exact barcode matches add one unit by default.
- Manual search results require an explicit selection when ambiguous.
- Show product name, unit price, and stock status in search results.
- Provide a visible empty-cart state.
- Warn before clearing a non-empty cart.
- Do not clear the cart if checkout fails.
- Display server-confirmed success only after the database transaction commits.
- Provide “View receipt”, “Print receipt”, and “New bill” actions after success.

### Sales screen

- Search by bill number.
- Date filter with a clear reset action.
- Paginated list.
- Receipt details page with print action.
- Do not provide an edit action that silently rewrites a completed invoice.
- If void/refund support is added later, implement an audited reversal workflow rather than deleting the sale.

### Settings screen

- Shop name.
- Optional address and phone.
- Optional tax registration fields if required by the shop.
- Receipt width: 58mm or 80mm.
- Pricing mode: GST-inclusive or GST-exclusive.
- Low-stock threshold.
- Receipt footer.
- Currency display: INR (₹).
- Shop state and transaction jurisdiction configuration if tax splitting is implemented.

Clearly explain that the pricing mode affects future billing calculations. Do not silently change historical receipts when settings change.

### Empty, loading, and error states

Every data screen must have:
- A useful empty state with a next action.
- A visible saving/loading state during requests.
- Inline validation errors.
- A recoverable error message when a request fails.
- No fake success state and no silent failure.

---

## 6. Technical Architecture

### Stack

- Python and Django.
- SQLite for the default single-computer deployment.
- Django ORM and migrations.
- Django templates.
- Tailwind CSS compiled locally.
- Vanilla JavaScript for scanner/cart interaction.
- Browser-native printing.
- Automated tests using Django's test framework.

Avoid introducing a large JavaScript framework unless a documented requirement justifies it.

### Suggested project structure

```text
offline-shop-pos/
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── core/
│   ├── products/
│   └── billing/
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── core/
│   ├── products/
│   ├── pos/
│   ├── sales/
│   └── receipts/
├── static/
│   ├── css/
│   │   ├── input.css
│   │   └── output.css
│   ├── js/
│   └── images/
├── tests/
├── requirements.txt
├── manage.py
├── design.md
└── README.md
```

Adjust the structure to the existing repository if one already exists. Do not move or overwrite existing data without a backup.

### Responsibilities

- **Models:** persistence, constraints, relationships, timestamps.
- **Forms:** server-side input validation.
- **Views:** HTTP request/response orchestration and permission checks.
- **Services:** checkout, tax calculation, stock changes, backup operations.
- **Templates:** accessible UI and receipt markup.
- **JavaScript:** temporary cart interactions, scanner handling, and display calculations only.
- **Tests:** models, validation, calculations, transactions, views, and critical user journeys.

Business rules must not live exclusively in JavaScript or templates.

### Local execution

- Bind to `127.0.0.1` by default; do not expose the development server to a public network by default.
- Provide exact Windows PowerShell setup and run commands in `README.md`.
- Include database migration and Tailwind build commands.
- Provide a reliable local launch procedure.
- Keep secrets and machine-specific paths out of source control.
- Use `DEBUG` and other environment settings deliberately; do not treat the development server as a production deployment server.

---

## 7. Data Model

Use Django models, migrations, explicit constraints, and appropriate indexes. Use `DecimalField` for money and rates.

### Product

Suggested fields:

- `id`: primary key.
- `name`: required text.
- `barcode`: optional unique value; normalize whitespace consistently.
- `selling_price`: Decimal field, non-negative.
- `stock_quantity`: non-negative integer for countable goods; use Decimal quantity only if fractional units are an actual requirement.
- `gst_rate`: validated Decimal percentage.
- `is_active`: boolean.
- `created_at`, `updated_at`.

Choose a documented precision for price and tax fields. Do not use Python binary floats for monetary arithmetic.

### Sale

Suggested fields:

- `id`: primary key.
- `bill_number`: unique, human-readable identifier.
- `created_at`: persisted timestamp.
- `subtotal`: Decimal.
- `taxable_total`: Decimal.
- `tax_total`: Decimal.
- `grand_total`: Decimal.
- `pricing_mode_snapshot`: inclusive/exclusive mode used for the sale.
- `status`: completed; add void/refund states only with an audited workflow.
- `payment_method`: optional validated choice if payment recording is included.

Use a consistent timezone policy and display local shop time in the interface.

### SaleItem

Suggested fields:

- `id`: primary key.
- `sale`: foreign key to Sale.
- `product`: nullable foreign key using a deletion policy that preserves history.
- `product_name_snapshot`.
- `barcode_snapshot`.
- `quantity`.
- `unit_price`.
- `gst_rate_snapshot`.
- `taxable_amount`.
- `tax_amount`.
- `line_total`.

Snapshots ensure old bills remain accurate after products are renamed, deactivated, or repriced.

### ShopSettings

A single configuration record may store shop details, receipt width, pricing mode, low-stock threshold, footer, and jurisdiction settings. Enforce a single active settings record through a deliberate application-level approach.

### StockMovement

Recommended for auditability:

- Product.
- Signed quantity change.
- Reason, such as opening stock, manual adjustment, or sale.
- Timestamp.
- Optional related sale.
- Optional note.

Stock changes should be traceable. Do not silently edit stock without recording the adjustment reason.

### Data constraints

- Unique bill number.
- Unique non-empty barcode.
- Non-negative stock and price.
- Valid GST rate.
- Positive sale-item quantity.
- Required snapshot values on historical sale items.
- Database indexes for barcode and commonly searched fields.

Validate at both application and database levels wherever practical.

---

## 8. GST and Money Calculation Policy

This software provides calculation mechanics; it does not guarantee statutory compliance. Confirm the shop's invoicing and tax obligations with a qualified professional before using receipts as formal tax invoices.

### Required configuration

The shop must explicitly choose whether product selling prices are:

- **GST-exclusive:** GST is added to the entered selling price.
- **GST-inclusive:** GST is already included in the entered selling price.

Do not mix modes within a bill unless specifically designed, tested, and clearly displayed.

### GST-exclusive formula

For quantity `q`, unit price `p`, and GST rate `r` percent:

- Taxable amount = `q × p`
- GST amount = `taxable amount × r / 100`
- Line total = `taxable amount + GST amount`

### GST-inclusive formula

For a line total `T` including GST at rate `r` percent:

- Taxable amount = `T / (1 + r / 100)`
- GST amount = `T - taxable amount`

### Rounding

- Use Python `Decimal` from validated decimal strings/values.
- Document a single rounding strategy.
- Quantize currency amounts consistently to two decimal places where appropriate.
- Choose whether rounding occurs at line level or invoice level and use that method consistently.
- Test fractional tax results and ensure displayed totals reconcile.

### CGST, SGST, and IGST

Only split GST after the shop's state and the relevant transaction jurisdiction are configured and validated. Do not infer the tax treatment from the computer's location. If jurisdiction is not configured, show a generic GST amount rather than guessing a split.

Store the tax rate and calculated amounts used on the sale item so future settings changes do not alter old bills.

---

## 9. Cart and Transaction Integrity

The browser cart is temporary and untrusted. The server is the source of truth.

### Checkout flow

1. Browser submits product identifiers, quantities, and a unique checkout request identifier.
2. Server validates the payload shape and limits.
3. Server loads current product records.
4. Server verifies active status and sufficient stock.
5. Server recalculates unit prices, taxable amounts, tax, and totals.
6. In one database transaction, create the Sale and SaleItem snapshots, deduct stock, and create stock movement records.
7. Commit the transaction.
8. Return the saved bill identifier and receipt URL.
9. Offer printing only for the saved receipt.

Use `transaction.atomic()` and appropriate locking/consistency safeguards for the chosen database. Do not assume `select_for_update()` provides identical locking semantics on SQLite and PostgreSQL.

### Duplicate-submission protection

- Generate a unique checkout request token for each intended sale.
- Store and enforce uniqueness for that token.
- If the same request is submitted again, return the original result rather than creating another bill.
- Disable the checkout button while the request is in flight, but do not rely on UI disabling alone.

### Failure handling

- If any validation or database operation fails, no partial sale or stock deduction may remain.
- Keep the cart available after recoverable failure.
- Show a useful message without exposing stack traces.
- If the connection is interrupted after commit, a retry using the same request token must not duplicate the sale.

### SQLite considerations

SQLite is suitable for one local checkout station with limited concurrent writes. Keep write transactions short and handle database-busy errors gracefully. For shared concurrent checkout across multiple machines, plan a tested PostgreSQL deployment rather than assuming SQLite is a multi-till database.

---

## 10. Barcode Scanner Behaviour

Most USB/Bluetooth keyboard-wedge scanners type a barcode into the focused input and may send Enter afterward.

- Keep the scan/search input visible and keyboard accessible.
- Focus it when the POS screen loads.
- Trim leading/trailing whitespace.
- Prefer exact barcode lookup.
- On an exact match, add one unit by default.
- If the product already exists in the cart, increment its quantity only if stock permits.
- Unknown barcode: show a non-blocking message and preserve the scanned value if useful.
- Do not interpret Enter in unrelated inputs as a scan.
- Do not steal focus while the user is editing quantity or another field.
- Provide manual product search for items without barcodes.
- Document how to configure the scanner suffix if the device does not send Enter.

Test with a real scanner and its actual configuration; do not claim universal compatibility without testing.

---

## 11. Receipt and Thermal Printing

### Receipt contents

- Shop name and configured contact information.
- Tax registration information only if entered and appropriate.
- Bill number and date/time.
- Item description.
- Quantity, unit price, and line amount.
- Taxable total and relevant GST breakdown.
- Subtotal, GST total, and grand total.
- Optional payment method.
- Configurable footer.

The receipt must render from saved sale snapshots, not current product data.

### Printing requirements

- Support configurable 58mm and 80mm paper widths.
- Provide an on-screen preview.
- Use `window.print()` on the saved receipt page.
- Hide navigation, buttons, controls, backgrounds, and decorative UI in print.
- Use black text on white background with compact, readable type.
- Avoid splitting item rows where practical.
- Reprint must never create a new sale or deduct stock.
- Explain that the browser print dialog and printer driver may require configuration.

Example baseline CSS:

```css
@media print {
  @page {
    size: 58mm auto;
    margin: 2mm;
  }

  html,
  body {
    width: 100%;
    margin: 0;
    padding: 0;
    background: #fff !important;
    color: #000 !important;
    font-family: Arial, sans-serif;
    font-size: 10pt;
  }

  .no-print {
    display: none !important;
  }

  .receipt {
    width: 100%;
    margin: 0;
    padding: 0;
    border: 0;
    box-shadow: none;
  }

  .receipt-item {
    break-inside: avoid;
  }
}
```

Implement a separate 80mm variant. Verify output on actual hardware and browser because continuous-paper height, margins, scaling, and cut behaviour depend on printer and driver settings. Browser printing does not guarantee silent printing.

---

## 12. Security, Privacy, and Local Data

- Use Django CSRF protection on state-changing requests.
- Validate all inputs on the server.
- Use Django ORM rather than interpolated SQL.
- Keep `DEBUG` off for any production-style deployment.
- Bind to loopback by default.
- Do not expose admin or debug endpoints to an untrusted network.
- Require appropriate local authorization if multiple people use the same computer or if the app becomes network-accessible.
- Protect destructive actions with confirmation.
- Do not log sensitive customer/payment data unnecessarily.
- Do not include passwords, secrets, database files, or live business data in source control.
- Document the location of the local database and backups.
- Provide a clear warning before database restore or destructive reset.

The initial product is local-only, but “offline” does not mean automatically secure against other users of the same Windows account or against disk failure.

---

## 13. Backup and Restore

Business data is critical and must be recoverable.

### Backup

- Provide a user-visible backup action and clear success/failure status.
- Use SQLite's backup API or another SQLite-safe mechanism for consistent backup; do not blindly copy a live database file.
- Save to a user-selected or documented backup directory outside the source-code directory.
- Use timestamped backup filenames.
- Preserve the original database.
- Include required media and configuration in the backup plan if such data is added.
- Do not claim success unless the backup file exists and the operation completes.

### Restore

- Require explicit confirmation.
- Create a safety backup of the current database first.
- Validate the selected backup before replacing current data.
- Never overwrite the only copy of the database.
- Provide a clear failure message and recovery instructions.
- Test restore into a separate database during development.
- Document what happens to the application process during restore.

A backup stored only on the same computer does not protect against theft or disk failure. Recommend periodic copies to external storage without making cloud connectivity mandatory.

---

## 14. SQLite-to-PostgreSQL Portability

Use Django's supported ORM, model fields, constraints, and migrations. Keep tax and checkout calculations in Python services.

- Avoid database-specific SQL in core business logic.
- Use explicit constraints and indexes.
- Use Decimal fields for money.
- Keep environment-based database configuration.
- Run automated tests against SQLite and PostgreSQL.
- Before migration: stop writes, create and verify a backup, migrate schema, import data, compare row counts and financial totals, run smoke tests, then switch the application.
- Keep the original backup until the migrated database has been verified.

A migration can be designed to preserve data, but zero data loss cannot be promised without a tested migration and recovery process.

---

## 15. Performance and Accessibility

- Use exact indexed barcode lookups.
- Paginate product and sales lists.
- Avoid loading the entire catalogue into the browser.
- Keep client-side JavaScript lightweight.
- Make all essential actions available from the keyboard.
- Label form controls programmatically.
- Use semantic headings and table structures.
- Provide visible focus states.
- Ensure errors and statuses are conveyed by text, not colour alone.
- Use readable contrast and touch targets.
- Avoid excessive animations and heavy assets.
- Keep receipt rendering independent from the full application shell.

---

## 16. Testing Strategy

### Product tests

- Create, edit, deactivate, and search products.
- Reject invalid names, negative values, invalid GST rates, and duplicate barcodes.
- Verify products without barcodes can be sold.
- Verify inactive products cannot be added to new bills.

### Billing tests

- Verify GST-exclusive calculations.
- Verify GST-inclusive calculations.
- Test zero and non-zero GST rates.
- Test rounding edge cases.
- Verify server totals do not trust client-submitted prices or totals.
- Verify old sale snapshots survive product edits.

### Stock and transaction tests

- Successful sale creates one bill and deducts stock once.
- Insufficient stock blocks checkout.
- Failed transaction leaves no partial sale, item, movement, or stock deduction.
- Repeated request token does not create duplicate bills.
- Product deactivation does not delete historical bills.
- Reprinting does not change inventory.

### UI and scanner tests

- Scanner field receives focus on load.
- Exact barcode match adds the correct product.
- Unknown barcode gives a useful message.
- Quantity edits and item removal update the displayed total.
- Failed checkout retains cart contents.
- Keyboard-only checkout is possible.

### Receipt tests

- 58mm and 80mm styles render correctly.
- Long item names and large carts remain readable.
- Receipt totals match the saved bill.
- Print controls are hidden in print output.
- Reprint uses historical snapshots.

### Offline and recovery tests

- Disconnect internet and test the full workflow.
- Verify all static assets are local.
- Create a backup and restore it into a test database.
- Verify product, sale, item, and stock counts after restore.
- Run migrations and tests against PostgreSQL before adopting it.

---

## 17. Implementation Plan

### Phase 0 — Repository and environment

- Inspect the repository and this design document.
- Identify existing code, environment, and data.
- Back up any existing database before changes.
- Create or verify the Python virtual environment.
- Install only required dependencies.
- Provide Windows PowerShell commands in README.

**Exit criteria:** Project starts locally and migrations run successfully.

### Phase 1 — Core and product inventory

- Build base layout and locally compiled Tailwind.
- Implement Product and ShopSettings.
- Build product list, create/edit, search, deactivate, and low-stock indicators.
- Add model and form tests.

**Exit criteria:** Product workflows work and validation tests pass.

### Phase 2 — POS and billing engine

- Build scanner-focused POS.
- Implement cart interactions.
- Implement Decimal-based tax calculation service.
- Implement atomic checkout, stock movements, and duplicate request protection.
- Add bill history and saved receipt view.
- Test transaction rollback and stock integrity.

**Exit criteria:** All billing and stock tests pass.

### Phase 3 — Printing

- Build receipt preview.
- Implement 58mm and 80mm print variants.
- Add print and reprint flows.
- Verify on real thermal hardware where available.

**Exit criteria:** Saved receipt totals are correct and repeat printing does not affect stock.

### Phase 4 — Dashboard and recovery

- Implement real dashboard metrics.
- Implement backup and safe restore.
- Document local data location and recovery steps.
- Test offline operation.

**Exit criteria:** Backup and restore tests pass; essential workflows need no internet.

### Phase 5 — Release hardening

- Run the full test suite.
- Check security configuration and error states.
- Test fresh installation and upgrade/migration path.
- Verify README setup steps on Windows.
- Document known limitations and printer setup.

**Exit criteria:** Fresh setup, checkout, reprint, backup, and restore have all been verified.

---

## 18. Release Checklist

Before calling v1 product-ready:

- [ ] Fresh installation succeeds using the README.
- [ ] Database migrations succeed from a clean database.
- [ ] Product create/edit/search/deactivate works.
- [ ] Barcode input works with a tested scanner.
- [ ] GST-inclusive and GST-exclusive modes are explicit and tested.
- [ ] Server recomputes all bill totals.
- [ ] Checkout is atomic and duplicate submissions are protected.
- [ ] Stock is deducted exactly once per completed sale.
- [ ] Old bills remain accurate after product edits.
- [ ] Sales history and reprint work.
- [ ] 58mm and 80mm receipts are verified on target hardware.
- [ ] Essential screens and assets work without internet.
- [ ] Backup and restore are tested.
- [ ] No fake metrics, placeholder actions, or silent failures remain.
- [ ] No secrets or live business data are committed.
- [ ] README contains Windows PowerShell commands and troubleshooting steps.
- [ ] Full automated test suite passes.
- [ ] Known limitations are documented.

---

## 19. Engineering Instructions for the Coding Agent

1. Read this entire `design.md` before editing files.
2. Inspect the existing project before deciding whether to create or modify structure.
3. Preserve existing business data and working functionality. Back up before any risky migration or destructive change.
4. Implement real end-to-end functionality; do not stop at mockups.
5. Use Django ORM and migrations, server-side validation, Decimal arithmetic, and atomic checkout transactions.
6. Keep essential frontend assets local and avoid CDN dependencies.
7. Run tests after each milestone and fix failures before proceeding.
8. Do not report a feature as complete unless it is implemented and verified.
9. Do not fabricate test results or claim physical printer compatibility without hardware testing.
10. Update the README with exact Windows PowerShell setup, run, migration, Tailwind build, backup, and troubleshooting commands.
11. If a requirement is ambiguous, choose the safest simple implementation and document the decision. Ask before making destructive changes or introducing major dependencies.
12. At each milestone, report changed files, implemented features, commands run, test results, and remaining limitations.

## 20. Definition of Done

A shopkeeper can use the application on one computer, without internet access, to add inventory, scan or search products, complete accurate GST-aware bills, update stock exactly once, find saved sales, print or reprint receipts, and back up and restore business data.

**Product standard:** fast at the counter, accurate in the database, readable on paper, usable offline, and recoverable after failure.
