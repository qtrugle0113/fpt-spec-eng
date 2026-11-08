CREATE TABLE IF NOT EXISTS customers_source (
 customer_id BIGINT PRIMARY KEY, customer_name TEXT NOT NULL,
 balance DECIMAL(18,4), registered_at DATETIME(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS customers_target LIKE customers_source;
INSERT INTO customers_source VALUES
 (1,'Nguyễn, An',12345.6789,'2026-01-01 12:30:00.123456'),
 (2,'Line one\nLine two',0,NULL),
 (3,'Quote "sample"',-12.3400,'2026-01-03 00:00:00')
ON DUPLICATE KEY UPDATE customer_id=customers_source.customer_id;
CREATE TABLE IF NOT EXISTS _aat_support_schema_version (
 singleton TINYINT PRIMARY KEY CHECK(singleton=1), version BIGINT NOT NULL, signature VARCHAR(64) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
INSERT INTO _aat_support_schema_version VALUES(1,1,'aat-support/1')
ON DUPLICATE KEY UPDATE singleton=_aat_support_schema_version.singleton;
CREATE TABLE IF NOT EXISTS _aat_batch_commits (
 target_identity VARCHAR(255) NOT NULL, run_uuid CHAR(36) NOT NULL,
 dataset_sha VARCHAR(64) NOT NULL, batch_index BIGINT NOT NULL,
 binding_sha VARCHAR(64) NOT NULL, row_count BIGINT NOT NULL,
 payload_sha VARCHAR(64) NOT NULL, strategy VARCHAR(16) NOT NULL, committed_at DATETIME(6) NOT NULL,
 PRIMARY KEY(target_identity,run_uuid,dataset_sha,batch_index)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS _aat_run_commits (
 target_identity VARCHAR(255) NOT NULL, run_uuid CHAR(36) NOT NULL,
 dataset_sha VARCHAR(64) NOT NULL, binding_sha VARCHAR(64) NOT NULL,
 total_loaded_rows BIGINT NOT NULL, replacement_authorization_sha VARCHAR(64), completed_at DATETIME(6) NOT NULL,
 PRIMARY KEY(target_identity,run_uuid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
