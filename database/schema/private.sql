-- DELIMOLD: initial SQLite schema, apply once to a NEW local database.
PRAGMA foreign_keys = ON;
BEGIN;

CREATE TABLE suppliers (
    id TEXT PRIMARY KEY NOT NULL,
    supplier_code TEXT NOT NULL COLLATE NOCASE UNIQUE, name TEXT NOT NULL, address TEXT, contact TEXT, email TEXT, phone TEXT, notes TEXT,
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_by TEXT, updated_by TEXT, archived_at TEXT
);

CREATE TABLE purchase_orders (
    id TEXT PRIMARY KEY NOT NULL,
    po_number TEXT NOT NULL COLLATE NOCASE UNIQUE, supplier_id TEXT NOT NULL REFERENCES suppliers(id), order_date TEXT NOT NULL, currency_code TEXT NOT NULL CHECK(length(currency_code) = 3), money_scale INTEGER NOT NULL DEFAULT 2 CHECK(money_scale BETWEEN 0 AND 6), status TEXT NOT NULL DEFAULT 'draft', commercial_terms TEXT, notes TEXT,
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_by TEXT, updated_by TEXT, archived_at TEXT
);

CREATE TABLE purchase_order_items (
    id TEXT PRIMARY KEY NOT NULL,
    po_id TEXT NOT NULL REFERENCES purchase_orders(id), line_number INTEGER NOT NULL CHECK(line_number > 0),
    mold_spec_external_id TEXT, transaction_type TEXT NOT NULL CHECK(transaction_type IN ('PURCHASE','REPAIR','MODIFICATION')),
    description_snapshot TEXT NOT NULL, quantity INTEGER NOT NULL CHECK(typeof(quantity) = 'integer' AND quantity > 0),
    unit_price_scaled INTEGER NOT NULL CHECK(typeof(unit_price_scaled) = 'integer' AND unit_price_scaled >= 0),
    discount_scaled INTEGER NOT NULL DEFAULT 0 CHECK(typeof(discount_scaled) = 'integer' AND discount_scaled >= 0),
    tax_scaled INTEGER NOT NULL DEFAULT 0 CHECK(typeof(tax_scaled) = 'integer' AND tax_scaled >= 0),
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_by TEXT, updated_by TEXT, archived_at TEXT,
    UNIQUE(po_id, line_number), CHECK(discount_scaled <= quantity * unit_price_scaled)
);

CREATE TABLE order_item_mold_links (
    id TEXT PRIMARY KEY NOT NULL,
    order_item_id TEXT NOT NULL REFERENCES purchase_order_items(id), mold_unit_external_id TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_by TEXT, updated_by TEXT, archived_at TEXT,
    UNIQUE(order_item_id, mold_unit_external_id)
);

CREATE TABLE private_attachments (
    id TEXT PRIMARY KEY NOT NULL,
    po_id TEXT NOT NULL REFERENCES purchase_orders(id), relative_path TEXT NOT NULL UNIQUE, original_name TEXT NOT NULL, mime_type TEXT,
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_by TEXT, updated_by TEXT, archived_at TEXT
);

CREATE TABLE private_audit (
    id TEXT PRIMARY KEY NOT NULL,
    actor_id TEXT NOT NULL, action TEXT NOT NULL, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, occurred_at TEXT NOT NULL, details_json TEXT NOT NULL
);

PRAGMA user_version = 1;
COMMIT;
