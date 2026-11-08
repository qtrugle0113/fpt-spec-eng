CREATE SCHEMA IF NOT EXISTS sample;
CREATE SCHEMA IF NOT EXISTS _aat_control;
CREATE TABLE IF NOT EXISTS sample.customers_source (
 customer_id bigint PRIMARY KEY, customer_name text NOT NULL,
 balance numeric(18,4), registered_at timestamp(6)
);
CREATE TABLE IF NOT EXISTS sample.customers_target (LIKE sample.customers_source INCLUDING ALL);
INSERT INTO sample.customers_source VALUES
 (1,'Nguyễn, An',12345.6789,'2026-01-01 12:30:00.123456'),
 (2,E'Line one\nLine two',0,NULL),
 (3,'Quote "sample"',-12.3400,'2026-01-03 00:00:00')
ON CONFLICT (customer_id) DO NOTHING;
CREATE TABLE IF NOT EXISTS _aat_control.support_schema_version (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton), version bigint NOT NULL, signature text NOT NULL
);
INSERT INTO _aat_control.support_schema_version VALUES (true,1,'aat-support/1') ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS _aat_control.batch_commits (
 target_identity text NOT NULL, run_uuid uuid NOT NULL, dataset_sha text NOT NULL,
 batch_index bigint NOT NULL, binding_sha text NOT NULL, row_count bigint NOT NULL,
 payload_sha text NOT NULL, strategy text NOT NULL, committed_at timestamptz NOT NULL,
 PRIMARY KEY(target_identity,run_uuid,dataset_sha,batch_index)
);
CREATE TABLE IF NOT EXISTS _aat_control.run_commits (
 target_identity text NOT NULL, run_uuid uuid NOT NULL, dataset_sha text NOT NULL,
 binding_sha text NOT NULL, total_loaded_rows bigint NOT NULL,
 replacement_authorization_sha text, completed_at timestamptz NOT NULL,
 PRIMARY KEY(target_identity,run_uuid)
);
