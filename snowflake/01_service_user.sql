-- linkml-metrics: service user that runs every agent call (session 3).
-- Run once from the setup connection; the public key is substituted at run time and never written here:
--
--   snow sql -c perso -f snowflake/01_service_user.sql -D "pubkey=$(grep -v -- '-----' ~/.ssh/linkml_svc_rsa.pub | tr -d '\n')"
--
-- Why: agent tool calls run with the caller's rights, secondary roles included (phase0_findings.md, section 3).
-- A human user with DEFAULT_SECONDARY_ROLES = ALL hands ACCOUNTADMIN to every tool call. This user has the
-- project role only and no secondary role by default. The admin user is not changed: other projects depend on it.
USE SECONDARY ROLES NONE;

USE ROLE USERADMIN;
CREATE USER LINKML_SVC
    TYPE = SERVICE
    RSA_PUBLIC_KEY = '&{pubkey}'
    DEFAULT_ROLE = LINKML_METRICS_ROLE
    DEFAULT_WAREHOUSE = LINKML_METRICS_WH
    DEFAULT_SECONDARY_ROLES = ()
    COMMENT = 'linkml-metrics: service user for every agent call';

USE ROLE SECURITYADMIN;
GRANT ROLE LINKML_METRICS_ROLE TO USER LINKML_SVC;

-- Readback.
SHOW GRANTS TO USER LINKML_SVC;
DESC USER LINKML_SVC;
