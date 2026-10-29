-- DELIMOLD: initial SQLite schema, apply once to a NEW local database.
PRAGMA foreign_keys = ON;
BEGIN;

CREATE TABLE categories (
    id TEXT PRIMARY KEY NOT NULL,
    code TEXT NOT NULL COLLATE NOCASE UNIQUE, name TEXT NOT NULL,
    archived_at TEXT
);

CREATE TABLE patterns (
    id TEXT PRIMARY KEY NOT NULL,
    code TEXT NOT NULL COLLATE NOCASE UNIQUE, name TEXT NOT NULL, land_ratio REAL CHECK(land_ratio BETWEEN 0 AND 100), svg_path TEXT, preview_path TEXT, status TEXT NOT NULL DEFAULT 'active', status_reason TEXT,
    archived_at TEXT
);

CREATE TABLE stickers (
    id TEXT PRIMARY KEY NOT NULL,
    code TEXT NOT NULL COLLATE NOCASE UNIQUE, name TEXT NOT NULL, image_path TEXT, status TEXT NOT NULL DEFAULT 'active', status_reason TEXT,
    archived_at TEXT
);

CREATE TABLE container_models (
    id TEXT PRIMARY KEY NOT NULL,
    code TEXT NOT NULL COLLATE NOCASE UNIQUE, model TEXT NOT NULL, od_sector_mm REAL CHECK(od_sector_mm > 0), sw_sector_mm REAL CHECK(sw_sector_mm > 0), segment_count INTEGER CHECK(segment_count > 0),
    archived_at TEXT
);

CREATE TABLE container_spacers (
    id TEXT PRIMARY KEY NOT NULL,
    container_model_id TEXT NOT NULL REFERENCES container_models(id), thickness_mm REAL NOT NULL CHECK(thickness_mm >= 0), resulting_od_mm REAL CHECK(resulting_od_mm > 0),
    archived_at TEXT,
    UNIQUE(container_model_id, thickness_mm), UNIQUE(id, container_model_id)
);

CREATE TABLE container_units (
    id TEXT PRIMARY KEY NOT NULL,
    container_model_id TEXT NOT NULL REFERENCES container_models(id), unit_number TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active', status_reason TEXT,
    archived_at TEXT,
    UNIQUE(container_model_id, unit_number)
);

CREATE TABLE mold_specs (
    id TEXT PRIMARY KEY NOT NULL,
    spec_code TEXT NOT NULL COLLATE NOCASE UNIQUE, tire_size TEXT NOT NULL, pattern_id TEXT NOT NULL REFERENCES patterns(id), category_id TEXT REFERENCES categories(id),
    archived_at TEXT
);

CREATE TABLE mold_units (
    id TEXT PRIMARY KEY NOT NULL,
    spec_id TEXT NOT NULL REFERENCES mold_specs(id), mold_number TEXT NOT NULL,
    curing_type TEXT, mold_type TEXT,
    segmented_role TEXT CHECK(segmented_role IN ('MAIN','SHARING')),
    main_unit_id TEXT REFERENCES mold_units(id),
    container_model_id TEXT REFERENCES container_models(id), spacer_id TEXT,
    owner TEXT, bladder TEXT, status TEXT NOT NULL DEFAULT 'active',
    archived_at TEXT,
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
    archived_at TEXT,
    UNIQUE(mold_unit_id, brand_name, marking_type)
);

CREATE TABLE publication_meta (
    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
    publication_id TEXT NOT NULL UNIQUE,
    source_revision INTEGER NOT NULL CHECK(source_revision > 0),
    source_updated_at TEXT NOT NULL,
    published_at TEXT NOT NULL,
    schema_version INTEGER NOT NULL CHECK(schema_version = 1)
);
PRAGMA user_version = 1;
COMMIT;
