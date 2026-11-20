-- =============================================================================
--  RetailPulse — 10 · Dedicated read-only application account (Phase 5)
-- =============================================================================
--  Run ONCE, as a MySQL administrator (root or your own admin account), AFTER
--  the database exists. It creates the account every script and notebook uses.
--
--  NO PASSWORD IS STORED IN THIS FILE. Replace the placeholder only in your
--  terminal session — never save a real password into this file or commit it:
--
--      1. choose a long random password (e.g. python3 -c "import secrets; print(secrets.token_urlsafe(32))")
--      2. put it in .env as MYSQL_PASSWORD (copy .env.example to .env)
--      3. run this script, typing the same password at the prompt:
--
--         mysql -u root -p      # or your admin user; then paste the statements
--                               # below with REPLACE_WITH_PASSWORD substituted
--
--  LEAST PRIVILEGE: every normal operation (exports, validators, notebooks,
--  sql/03-06, 08, 09) only reads, so the account gets SELECT on this one
--  schema and nothing else: no INSERT/UPDATE/DELETE, no DDL, no FILE, no
--  GRANT, no access to other schemas. Rebuilding the database (sql/01, 02,
--  07) is an administrator task and is never run with this account.
--
--  Both host forms are created because a TCP connection to 127.0.0.1 and a
--  socket connection to localhost are matched as different hosts.
-- =============================================================================

CREATE USER IF NOT EXISTS 'retailpulse_app'@'localhost' IDENTIFIED BY 'REPLACE_WITH_PASSWORD';
CREATE USER IF NOT EXISTS 'retailpulse_app'@'127.0.0.1' IDENTIFIED BY 'REPLACE_WITH_PASSWORD';

GRANT SELECT ON retailpulse.* TO 'retailpulse_app'@'localhost';
GRANT SELECT ON retailpulse.* TO 'retailpulse_app'@'127.0.0.1';

-- To change the password later (then update .env):
--   ALTER USER 'retailpulse_app'@'localhost' IDENTIFIED BY '...';
--   ALTER USER 'retailpulse_app'@'127.0.0.1' IDENTIFIED BY '...';

-- Verify:
SHOW GRANTS FOR 'retailpulse_app'@'localhost';
SHOW GRANTS FOR 'retailpulse_app'@'127.0.0.1';
