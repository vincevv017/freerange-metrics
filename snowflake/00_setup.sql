-- linkml-metrics: one-time account setup.
-- Run as ACCOUNTADMIN. Idempotent: every CREATE is IF NOT EXISTS, every GRANT can be replayed.
-- After this script, all work runs as LINKML_METRICS_ROLE on LINKML_METRICS_WH.
--
--   snow sql -c perso --role ACCOUNTADMIN -f snowflake/00_setup.sql -D "admin_user=<ADMIN_USER>"
--
-- admin_user is the human user that runs setup and the probes; it is substituted at run time, never written here.

-- The admin user has DEFAULT_SECONDARY_ROLES = ALL: without this, every role granted to the user
-- (ACCOUNTADMIN included) silently adds its privileges to the session. Every script starts here.
USE SECONDARY ROLES NONE;
USE ROLE ACCOUNTADMIN;

-- 1. Project role, inside the SYSADMIN hierarchy so SYSADMIN keeps visibility of its objects.
CREATE ROLE IF NOT EXISTS LINKML_METRICS_ROLE
    COMMENT = 'linkml-metrics: owns LINKML_METRICS, runs every phase after setup';
GRANT ROLE LINKML_METRICS_ROLE TO ROLE SYSADMIN;
GRANT ROLE LINKML_METRICS_ROLE TO USER &{admin_user};

-- 2. Dedicated warehouse. XSMALL, suspended until first use, suspends after 60 s idle.
CREATE WAREHOUSE IF NOT EXISTS LINKML_METRICS_WH
    WAREHOUSE_SIZE = XSMALL
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'linkml-metrics: project warehouse';
GRANT USAGE, OPERATE ON WAREHOUSE LINKML_METRICS_WH TO ROLE LINKML_METRICS_ROLE;

-- 3. Database owned by the project role. COPY CURRENT GRANTS keeps the script replayable.
CREATE DATABASE IF NOT EXISTS LINKML_METRICS
    COMMENT = 'linkml-metrics: synthetic stock-coverage dataset and generated objects';
GRANT OWNERSHIP ON DATABASE LINKML_METRICS TO ROLE LINKML_METRICS_ROLE COPY CURRENT GRANTS;

-- 4. Cortex access (agents, Analyst, AI functions) for the project role.
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE LINKML_METRICS_ROLE;

-- 5. Schema RAW, created by the project role so the role owns it.
--    Other schemas arrive with the phases that need them.
USE ROLE LINKML_METRICS_ROLE;
CREATE SCHEMA IF NOT EXISTS LINKML_METRICS.RAW
    COMMENT = 'linkml-metrics: synthetic source tables (dims and facts)';

-- Ownership already implies these; they are granted explicitly so the intent survives
-- an ownership transfer and reads plainly in SHOW GRANTS.
GRANT CREATE SEMANTIC VIEW ON SCHEMA LINKML_METRICS.RAW TO ROLE LINKML_METRICS_ROLE;
GRANT CREATE PROCEDURE     ON SCHEMA LINKML_METRICS.RAW TO ROLE LINKML_METRICS_ROLE;
GRANT CREATE AGENT         ON SCHEMA LINKML_METRICS.RAW TO ROLE LINKML_METRICS_ROLE;

-- 6. Readback.
SHOW GRANTS TO ROLE LINKML_METRICS_ROLE;
SHOW GRANTS ON SCHEMA LINKML_METRICS.RAW;
