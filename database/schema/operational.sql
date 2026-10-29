-- DELIMOLD: initial SQLite schema, apply once to a NEW local database.
PRAGMA foreign_keys = ON;
BEGIN;

CREATE TABLE categories (
    id TEXT PRIMARY KEY NOT NULL,
    code TEXT NOT NULL COLLATE NOCASE UNIQUE, name TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_by TEXT, updated_by TEXT, archived_at TEXT
);

CREATE TABLE patterns (
    id TEXT PRIMARY KEY NOT NULL,
    code TEXT NOT NULL COLLATE NOCASE UNIQUE, name TEXT NOT NULL, land_ratio REAL CHECK(land_ratio BETWEEN 0 AND 100), svg_path TEXT, preview_path TEXT, status TEXT NOT NULL DEFAULT 'active', status_reason TEXT,
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_by TEXT, updated_by TEXT, archived_at TEXT
);

CREATE TABLE stickers (
    id TEXT PRIMARY KEY NOT NULL,
    code TEXT NOT NULL COLLATE NOCASE UNIQUE, name TEXT NOT NULL, image_path TEXT, status TEXT NOT NULL DEFAULT 'active', status_reason TEXT,
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_by TEXT, updated_by TEXT, archived_at TEXT
);

CREATE TABLE container_models (
    id TEXT PRIMARY KEY NOT NULL,
    code TEXT NOT NULL COLLATE NOCASE UNIQUE, model TEXT NOT NULL, od_sector_mm REAL CHECK(od_sector_mm > 0), sw_sector_mm REAL CHECK(sw_sector_mm > 0), segment_count INTEGER CHECK(segment_count > 0),
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_by TEXT, updated_by TEXT, archived_at TEXT
);

CREATE TABLE container_spacers (
    id TEXT PRIMARY KEY NOT NULL,
    container_model_id TEXT NOT NULL REFERENCES container_models(id), thickness_mm REAL NOT NULL CHECK(thickness_mm >= 0), resulting_od_mm REAL CHECK(resulting_od_mm > 0),
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_by TEXT, updated_by TEXT, archived_at TEXT,
    UNIQUE(container_model_id, thickness_mm), UNIQUE(id, container_model_id)
);

CREATE TABLE container_units (
    id TEXT PRIMARY KEY NOT NULL,
    container_model_id TEXT NOT NULL REFERENCES container_models(id), unit_number TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active', status_reason TEXT,
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_by TEXT, updated_by TEXT, archived_at TEXT,
    UNIQUE(container_model_id, unit_number)
);

CREATE TABLE mold_specs (
    id TEXT PRIMARY KEY NOT NULL,
    spec_code TEXT NOT NULL COLLATE NOCASE UNIQUE, tire_size TEXT NOT NULL, pattern_id TEXT NOT NULL REFERENCES patterns(id), category_id TEXT REFERENCES categories(id),
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_by TEXT, updated_by TEXT, archived_at TEXT
);

CREATE TABLE mold_units (
    id TEXT PRIMARY KEY NOT NULL,
    spec_id TEXT NOT NULL REFERENCES mold_specs(id), mold_number TEXT NOT NULL,
    curing_type TEXT, mold_type TEXT,
    segmented_role TEXT CHECK(segmented_role IN ('MAIN','SHARING')),
    main_unit_id TEXT REFERENCES mold_units(id),
    container_model_id TEXT REFERENCES container_models(id), spacer_id TEXT,
    owner TEXT, bladder TEXT, status TEXT NOT NULL DEFAULT 'active',
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_by TEXT, updated_by TEXT, archived_at TEXT,
    UNIQUE(spec_id, mold_number),
    FOREIGN KEY(spacer_id, container_model_id) REFERENCES container_spacers(id, container_model_id),
    CHECK(spacer_id IS NULL OR container_model_id IS NOT NULL),
    CHECK(main_unit_id IS NULL OR main_unit_id <> id),
    CHECK(CASE WHEN segmented_role = 'SHARING' THEN main_unit_id IS NOT NULL ELSE main_unit_id IS NULL END),
    CHECK(segmented_role IS NULL OR (mold_type IS NOT NULL AND mold_type = 'SEGMENTED')),
    CHECK(curing_type IS NULL OR curing_type <> 'AIRBAG' OR bladder IS NULL)
);

CREATE TABLE mold_brands (
    id TEXT PRIMARY KEY NOT NULL,
    mold_unit_id TEXT NOT NULL REFERENCES mold_units(id), brand_name TEXT NOT NULL, marking_type TEXT NOT NULL CHECK(marking_type IN ('PLUG','PLAT')),
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_by TEXT, updated_by TEXT, archived_at TEXT,
    UNIQUE(mold_unit_id, brand_name, marking_type)
);

CREATE TRIGGER validate_sharing_insert BEFORE INSERT ON mold_units
WHEN NEW.segmented_role = 'SHARING'
BEGIN
    SELECT RAISE(ABORT, 'Sharing requires an active segmented Main') WHERE NOT EXISTS (
        SELECT 1 FROM mold_units WHERE id = NEW.main_unit_id
        AND segmented_role = 'MAIN' AND mold_type = 'SEGMENTED' AND archived_at IS NULL);
END;

CREATE TRIGGER validate_sharing_update BEFORE UPDATE ON mold_units
WHEN NEW.segmented_role = 'SHARING'
BEGIN
    SELECT RAISE(ABORT, 'Sharing requires an active segmented Main') WHERE NOT EXISTS (
        SELECT 1 FROM mold_units WHERE id = NEW.main_unit_id
        AND segmented_role = 'MAIN' AND mold_type = 'SEGMENTED' AND archived_at IS NULL);
END;

CREATE TRIGGER protect_main BEFORE UPDATE ON mold_units
WHEN EXISTS(SELECT 1 FROM mold_units WHERE main_unit_id = OLD.id AND archived_at IS NULL)
AND (NEW.segmented_role IS NOT 'MAIN' OR NEW.mold_type IS NOT 'SEGMENTED' OR NEW.archived_at IS NOT NULL)
BEGIN SELECT RAISE(ABORT, 'Main is referenced by active Sharing'); END;

CREATE TABLE projects (
    id TEXT PRIMARY KEY NOT NULL,
    project_code TEXT NOT NULL COLLATE NOCASE UNIQUE, title TEXT NOT NULL, owner_user_id TEXT, status TEXT NOT NULL DEFAULT 'planned', notes TEXT,
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_by TEXT, updated_by TEXT, archived_at TEXT
);

CREATE TABLE project_documents (
    id TEXT PRIMARY KEY NOT NULL,
    project_id TEXT NOT NULL REFERENCES projects(id), document_code TEXT NOT NULL, title TEXT NOT NULL, document_type TEXT, status TEXT,
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_by TEXT, updated_by TEXT, archived_at TEXT,
    UNIQUE(project_id, document_code)
);

CREATE TABLE document_files (
    id TEXT PRIMARY KEY NOT NULL,
    document_id TEXT NOT NULL REFERENCES project_documents(id), version_number INTEGER NOT NULL CHECK(version_number > 0), relative_path TEXT NOT NULL UNIQUE, original_name TEXT NOT NULL, mime_type TEXT, size_bytes INTEGER CHECK(size_bytes >= 0),
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_by TEXT, updated_by TEXT, archived_at TEXT,
    UNIQUE(document_id, version_number)
);

CREATE TABLE project_mold_links (
    id TEXT PRIMARY KEY NOT NULL,
    project_id TEXT NOT NULL REFERENCES projects(id), mold_spec_id TEXT REFERENCES mold_specs(id), mold_unit_id TEXT REFERENCES mold_units(id),
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_by TEXT, updated_by TEXT, archived_at TEXT,
    CHECK((mold_spec_id IS NOT NULL) <> (mold_unit_id IS NOT NULL))
);

CREATE UNIQUE INDEX project_spec_unique ON project_mold_links(project_id, mold_spec_id) WHERE mold_spec_id IS NOT NULL;
CREATE UNIQUE INDEX project_unit_unique ON project_mold_links(project_id, mold_unit_id) WHERE mold_unit_id IS NOT NULL;

CREATE TABLE audit_events (
    id TEXT PRIMARY KEY NOT NULL,
    entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, action TEXT NOT NULL, actor_id TEXT NOT NULL, occurred_at TEXT NOT NULL, changes_json TEXT NOT NULL
);

CREATE TABLE publication_outbox (
    source_revision INTEGER PRIMARY KEY AUTOINCREMENT,
    publication_id TEXT NOT NULL UNIQUE,
    source_updated_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','sending','published','failed','superseded')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts >= 0),
    last_error TEXT, published_at TEXT
);
CREATE INDEX outbox_pending ON publication_outbox(status, source_revision);

CREATE VIEW publish_categories AS SELECT id, code, name, archived_at FROM categories;
CREATE VIEW publish_patterns AS SELECT id, code, name, land_ratio, svg_path, preview_path, status, status_reason, archived_at FROM patterns;
CREATE VIEW publish_stickers AS SELECT id, code, name, image_path, status, status_reason, archived_at FROM stickers;
CREATE VIEW publish_container_models AS SELECT id, code, model, od_sector_mm, sw_sector_mm, segment_count, archived_at FROM container_models;
CREATE VIEW publish_container_spacers AS SELECT id, container_model_id, thickness_mm, resulting_od_mm, archived_at FROM container_spacers;
CREATE VIEW publish_container_units AS SELECT id, container_model_id, unit_number, status, status_reason, archived_at FROM container_units;
CREATE VIEW publish_mold_specs AS SELECT id, spec_code, tire_size, pattern_id, category_id, archived_at FROM mold_specs;
CREATE VIEW publish_mold_units AS SELECT id, spec_id, mold_number, curing_type, mold_type, segmented_role, main_unit_id, container_model_id, spacer_id, owner, bladder, status, archived_at FROM mold_units;
CREATE VIEW publish_mold_brands AS SELECT id, mold_unit_id, brand_name, marking_type, archived_at FROM mold_brands;
PRAGMA user_version = 1;
COMMIT;
