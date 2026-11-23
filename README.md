#### Expiry ERP

Retail & warehouse inventory system focused on **batch-level expiry control (FEFO)**, multi-branch isolation, alerts, barcode scanning, and operational reports. 

Built with **Django**, **PostgreSQL**, and a dark Tailwind-style UI. 

#### Overview

Expiry ERP helps stores and warehouses: 

* Track products and batches with manufacturing, sell-by, salvage, and hard expiry dates
* Prioritize stock using **FEFO** (First Expired, First Out)
* Separate data by **branch / warehouse**
* Alert managers about near-expiry and expired stock
* Scan barcodes to search batches and products
* Run expiry and stock reports (with Excel export)

**Typical Users:** Warehouse staff, managers, and superusers on office LAN/Wi‑Fi (browser). A mobile API and offline APK sync design are planned separately. 

#### Key Features

#### Inventory

* **Products:** icode (auto series from DB ID, e.g., 100001), scode, category, UOM, prices, reorder level, and branch
* **Batches:** Batch number, dates, quantity, and status (active / expired / quarantined)
* **Categories:** Global across branches; optional per-category expiry threshold (days)
* **Branches:** Warehouses with full CRUD for managers/superusers
* **Stock on Hand (SoH):** Automatically aggregated from active batches
* **Bulk Upload:** Excel import for products and batches

#### Expiry & Alerts

* **Dashboard Cards:** Total products, SoH, near-expiry count, and expired count
* **Expiry Tables:** Branch-scoped **Expiring Soon** and **Expired** tables
* **Dedicated Views:** Full pages with search and pagination
* **Manual Checks:** On-demand **Run Expiry Check** button to generate notifications
* **Scheduled Checks:** Optional Celery task (check_expiry_alerts) for automated runs
* **Notification Center:** Mark as read, delete individual alerts, or clear all read alerts

#### Multi-Branch Isolation

* Users are assigned to one or more branches (Many-to-Many)
* **Superusers** can view all active branches
* Staff with no assigned branches can be auto-assigned to **Main**
* Session-based **active branch** with a navbar branch switcher
* Products, batches, dashboard stats, scanner searches, and reports are strictly filtered by the active branch
* Categories, user accounts, and app settings remain **global**

#### Users & Access

* Custom user model with **roles** (superuser, manager, staff)
* Superuser-only user management UI (create, edit, delete)
* Assign branches on user creation and migrate branches on edit
* Standard Django session authentication for web, plus JWT endpoints for future mobile/API clients

#### Operations UI

* **Responsive Lists:** Search, pagination, and consistent slate/teal dark cards
* **Barcode / QR Scanner:** Camera scanning and manual entry routed directly to batch search
* **Reporting:** Expiry window selector, stock vs. expiry analysis, and Excel export
* **Smooth UX:** Loading indicators and transition overlays for login and navigation

#### Tech Stack

LayerTechnology
****Backend****
Django 4 / 5 / 6
****Database****
PostgreSQL (production); SQLite for local experiments only
****Authentication****
Django sessions + rest_framework_simplejwt
****API****
Django REST Framework, drf-spectacular (OpenAPI schema)
****Background Tasks****
Celery (optional; manual expiry checks work without a worker)
****Frontend****
Django templates, Tailwind-like utility classes, Alpine.js (modals)
****Data Import/Export****
openpyxl, django-import-export / tablib
****Audit History****
django-simple-history (where enabled on models)
****Production Host****
Windows office PC, Waitress, NSSM service, scheduled pg_dump backups

#### Project Architecture

#### Main Apps

AppResponsibility
**inventory**
Products, batches, categories, branches, dashboard, scanner, bulk upload
**alerts**
Notifications and expiry check task integration
**reports**
Expiry reports, stock-expiry reports, and Excel exports
**core**
Custom user model, user CRUD, root redirects, and JWT token views
**config**
Project settings, root URLs, and WSGI *(verify exact name via *wsgi.py)*

#### Core Models (inventory)

* **Branch:** name, code, is_active
* **Category:** name, expiry_threshold_days (global)
* **Product:** name, icode, scode, category, prices, branch, and SoH property
* **Batch:** product, batch_number, dates, quantity, status, plus helper methods (days_to_expiry, expiry_status_display, get_expiry_color, is_near_expiry)
* **StockMovement:** Audit trail for stock receipts, issues, and adjustments

**Note:** icode is generated in the **100001** series from the product primary key to maintain a stable business code alongside pk. 

#### Directory Layout

Show Code

Hide Code

Download diagram SVG

ASCII

expiry-erp/
├── config/                 # Settings, URLs, WSGI
├── inventory/              # Models, views, templates, branch helpers
├── alerts/                 # Notification models and Celery tasks
├── reports/                # Expiry & stock report views and Excel builders
├── core/                   # CustomUser, user management CRUD, JWT views
├── templates/
├── static/
├── manage.py
├── requirements.txt
└── README.md

Use code with caution.

Copy code text to clipboard.

**Office Server Layout (Windows):** 

Show Code

Hide Code

Download diagram SVG

ASCII

C:\Apps\ExpiryERP\
├── app\                    # Django project root
├── .venv\                  # Python virtual environment
├── scripts\                # install.bat, update.bat, backup_db.bat
├── backups\                # Automated pg_dump files
└── logs\                   # Service and application logs

Use code with caution.

Copy code text to clipboard.

#### Development Setup

#### Prerequisites

* Python 3.12+
* PostgreSQL 14+ (recommended)
* Git (optional)

#### Installation Steps

1. **Clone the repository and navigate to the project directory:** 

bash

cd expiry-erp   # or C:\Apps\ExpiryERP\app

Use code with caution.

Copy code text to clipboard.
2. **Create and activate a virtual environment:** 

bash

python -m venv .venv

# Windows:
.venv\Scripts\activate

# Linux/macOS:
source .venv/bin/activate

Use code with caution.

Copy code text to clipboard.
3. **Install dependencies:** 

bash

pip install -r requirements.txt

Use code with caution.

Copy code text to clipboard.
4. **Configure environment variables:**
Create a .env file in the project root: 

env

DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://USER:PASSWORD@127.0.0.1:5432/expiry_erp

Use code with caution.

Copy code text to clipboard.
5. **Run migrations, create a superuser, and start the server:** 

bash

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

Use code with caution.

Copy code text to clipboard.
6. **Initial Configuration:** 

  * Open http://127.0.0.1:8000/ in your browser.
  * Create at least one **Branch** (e.g., *Main Store*).
  * Assign branches to non-superuser accounts under the **Users** menu.

#### Production & Operations

#### Office Desktop Deployment (Windows 11)

* **Hosting:** Single Windows 11 office PC on LAN/Wi‑Fi running local PostgreSQL.
* **Application Server:** Waitress serving on 0.0.0.0:8000, managed as an auto-starting Windows service via **NSSM**.
* **Client Access:** Accessible on the local network via http://<office-pc-ip>:8000.
* **Backups:** Daily scheduled pg_dump backups saved to backups\.
* **Updates:** Replace application code and execute scripts\update.bat (backs up DB → stops service → runs migrations → collects static files → restarts service).
* **Camera Scanner:** Use HTTPS or a custom domain (e.g., Cloudflare Tunnel) if mobile devices need camera barcode access off-localhost.

#### Celery (Optional)

Expiry notifications are triggered via alerts.tasks.check_expiry_alerts: 

* **Without Celery:** Clicking **Run Expiry Check** on the dashboard executes the check synchronously.
* **With Celery:** Run a Celery worker and Celery Beat alongside Redis or RabbitMQ for automated daily checks.

#### Security Checklist

* [ ] Set DEBUG=False in production
* [ ] Generate a strong, unique SECRET_KEY
* [ ] Add the office IP/domain to ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS
* [ ] Enforce HTTPS for non-localhost mobile camera access
* [ ] Restrict user administration views to superusers only
* [ ] Never commit .env files or database credentials to version control
* [ ] Always back up the database before running migrations or deploying updates

#### Reference

#### URL Highlights

AreaURL Names
****Dashboard****
inventory:dashboard
****Products & Batches****
inventory:product_list, inventory:batch_list
****Branches****
inventory:branch_list, inventory:switch_branch
****Expiry Views****
inventory:expiring_soon, inventory:expired_batches
****Scanner****
inventory:scanner
****Users****
core:user_list, core:user_create, core:user_update
****Reports****
reports:… (expiry and stock reports)
****Notifications****
alerts:notification_list

#### User Roles

RoleAccess Level
****superuser****
Access to all branches, user management, and full system configuration
****manager****
Day-to-day operations, branch management, and elevated expiry alerts
****staff****
Restricted to assigned branches; day-to-day inventory handling

**Note:** Always enforce branch filtering in views using helpers such as require_active_branch() and get_user_branches(). 

#### API & Mobile Roadmap

#### Current API Endpoints

* **Authentication:** POST /api/token/ and POST /api/token/refresh/
* **Resources:** DRF ViewSets are available for categories, products, batches, and stock movements.

### Planned Offline APK Sync (Option C)
Django remains the central source of truth while the Android APK operates as an offline-first client:
1. **Authenticate:** Log in and fetch user profile/branches via `/api/me/`.
2. **Sync Down:** Pull branch-scoped products and batches (initial bootstrap + delta syncs) into device SQLite.
3. **Offline Work:** Record stock movements locally on the device.
4. **Sync Up:** Push queued stock movements using client-generated idempotency keys.
5. **Refresh:** Pull updated quantities back to the device.

---

## Development Conventions

* **List Pages:** Must support search and pagination while preserving active query parameters in pagination links.
* **UI Consistency:** Maintain the slate/teal dark theme across all tables, forms, and cards.
* **Branch Scoping on Creation:** Automatically assign `branch` from the user's active session branch when creating products—never trust client-submitted branch IDs.
* **Batch Filtering:** Populate batch product dropdowns strictly with products belonging to the active branch.
* **Excel Exports:** Call model helpers as methods (e.g., `days_to_expiry()`) rather than accessing them as bare attributes.

---

## License & Maintainers

* **License:** Proprietary / internal use only unless otherwise specified by the project owner.
* **Maintainers:** Maintained in-house by IT. Refer to internal office runbooks and `scripts/` helpers for deployment, branch assignment, and backup restoration procedures.
