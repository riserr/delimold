-- DELIMOLD: initial SQLite schema, apply once to a NEW local database.
PRAGMA foreign_keys = ON;
BEGIN;

CREATE TABLE users (
    id TEXT PRIMARY KEY NOT NULL,
    login TEXT NOT NULL COLLATE NOCASE UNIQUE, display_name TEXT NOT NULL, auth_method TEXT NOT NULL CHECK(auth_method IN ('LOCAL','WINDOWS')), password_hash TEXT, windows_subject TEXT UNIQUE, enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)),
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    created_by TEXT, updated_by TEXT, archived_at TEXT,
    CHECK((auth_method = 'LOCAL' AND password_hash IS NOT NULL AND length(password_hash) > 0 AND windows_subject IS NULL) OR (auth_method = 'WINDOWS' AND windows_subject IS NOT NULL AND password_hash IS NULL))
);

CREATE TABLE roles (
    id TEXT PRIMARY KEY NOT NULL,
    code TEXT NOT NULL UNIQUE
);

CREATE TABLE permissions (
    id TEXT PRIMARY KEY NOT NULL,
    resource TEXT NOT NULL, action TEXT NOT NULL,
    UNIQUE(resource, action)
);

CREATE TABLE user_roles (
    user_id TEXT NOT NULL REFERENCES users(id), role_id TEXT NOT NULL REFERENCES roles(id),
    PRIMARY KEY(user_id, role_id)
);
CREATE TABLE role_permissions (
    role_id TEXT NOT NULL REFERENCES roles(id), permission_id TEXT NOT NULL REFERENCES permissions(id),
    PRIMARY KEY(role_id, permission_id)
);
CREATE TABLE sessions (
    token_hash TEXT PRIMARY KEY NOT NULL, user_id TEXT NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL, expires_at TEXT NOT NULL, revoked_at TEXT,
    CHECK(expires_at > created_at)
);
CREATE TABLE auth_audit (
    id TEXT PRIMARY KEY NOT NULL,
    actor_id TEXT, action TEXT NOT NULL, occurred_at TEXT NOT NULL, details_json TEXT NOT NULL
);

INSERT INTO roles(id, code) VALUES ('superuser','SUPERUSER'), ('engineer','ENGINEER'), ('viewer','VIEWER');
INSERT INTO permissions(id,resource,action) VALUES ('operational.read','operational','read');
INSERT INTO role_permissions VALUES ('superuser','operational.read');
INSERT INTO role_permissions VALUES ('engineer','operational.read');
INSERT INTO role_permissions VALUES ('viewer','operational.read');
INSERT INTO permissions(id,resource,action) VALUES ('operational.write','operational','write');
INSERT INTO role_permissions VALUES ('superuser','operational.write');
INSERT INTO role_permissions VALUES ('engineer','operational.write');
INSERT INTO permissions(id,resource,action) VALUES ('operational.export','operational','export');
INSERT INTO role_permissions VALUES ('superuser','operational.export');
INSERT INTO role_permissions VALUES ('engineer','operational.export');
INSERT INTO role_permissions VALUES ('viewer','operational.export');
INSERT INTO permissions(id,resource,action) VALUES ('development.read','development','read');
INSERT INTO role_permissions VALUES ('superuser','development.read');
INSERT INTO role_permissions VALUES ('engineer','development.read');
INSERT INTO permissions(id,resource,action) VALUES ('development.write','development','write');
INSERT INTO role_permissions VALUES ('superuser','development.write');
INSERT INTO role_permissions VALUES ('engineer','development.write');
INSERT INTO permissions(id,resource,action) VALUES ('development.export','development','export');
INSERT INTO role_permissions VALUES ('superuser','development.export');
INSERT INTO role_permissions VALUES ('engineer','development.export');
INSERT INTO permissions(id,resource,action) VALUES ('private.read','private','read');
INSERT INTO role_permissions VALUES ('superuser','private.read');
INSERT INTO permissions(id,resource,action) VALUES ('private.write','private','write');
INSERT INTO role_permissions VALUES ('superuser','private.write');
INSERT INTO permissions(id,resource,action) VALUES ('private.export','private','export');
INSERT INTO role_permissions VALUES ('superuser','private.export');
INSERT INTO permissions(id,resource,action) VALUES ('accounts.manage','accounts','manage');
INSERT INTO role_permissions VALUES ('superuser','accounts.manage');
INSERT INTO permissions(id,resource,action) VALUES ('system.configure','system','configure');
INSERT INTO role_permissions VALUES ('superuser','system.configure');
INSERT INTO permissions(id,resource,action) VALUES ('system.restore','system','restore');
INSERT INTO role_permissions VALUES ('superuser','system.restore');
PRAGMA user_version = 1;
COMMIT;
