CREATE TABLE sensor (
    sensor_id INTEGER NOT NULL,
    sensor_desc TEXT NOT NULL,
    sensor_lat REAL NOT NULL,
    sensor_lon REAL NOT NULL,
    sensor_isOutdoor INTEGER NOT NULL,
    sensor_dir1 VARCHAR(5),
    sensor_dir2 VARCHAR(5),
    sensor_note TEXT,
    CONSTRAINT pk_sensor PRIMARY KEY (sensor_id),
    CONSTRAINT chk_sensor_isOutdoor CHECK (sensor_isOutdoor IN (0, 1)),
    CONSTRAINT chk_sensor_dir1 CHECK (sensor_dir1 IN ('East', 'North')),
    CONSTRAINT chk_sensor_dir2 CHECK (sensor_dir2 IN ('West', 'South'))
);

CREATE TABLE refuge (
    refuge_id INTEGER NOT NULL,
    refuge_cat VARCHAR(20) NOT NULL,
    refuge_name TEXT NOT NULL,
    refuge_lat REAL NOT NULL,
    refuge_lon REAL NOT NULL,
    refuge_tier INTEGER NOT NULL,
    refuge_area REAL,
    refuge_geometryJson TEXT,
    refuge_src VARCHAR(50) NOT NULL,
    refuge_srcAssetId TEXT NOT NULL,
    CONSTRAINT pk_refuge PRIMARY KEY (refuge_id),
    CONSTRAINT chk_refuge_tier CHECK (refuge_tier BETWEEN 1 AND 3)
);

CREATE TABLE sensor_refuge (
    sr_id INTEGER NOT NULL,
    sensor_id INTEGER NOT NULL,
    refuge_id INTEGER NOT NULL,
    sr_distance REAL NOT NULL,
    CONSTRAINT pk_sr PRIMARY KEY (sr_id),
    CONSTRAINT uq_sr UNIQUE (sensor_id, refuge_id)
);

ALTER TABLE sensor_refuge 
ADD CONSTRAINT fk_sr_sensor FOREIGN KEY (sensor_id) REFERENCES sensor(sensor_id);

ALTER TABLE sensor_refuge
ADD CONSTRAINT fk_sr_refuge FOREIGN KEY (refuge_id) REFERENCES refuge(refuge_id);

CREATE TABLE crowd_baseline (
    cb_id INTEGER NOT NULL,
    sensor_id INTEGER NOT NULL,
    cb_dayofweek INTEGER NOT NULL,
    cb_hourofday INTEGER NOT NULL,
    cb_dir1 INTEGER NOT NULL,
    cb_dir2 INTEGER NOT NULL,
    cb_totaldirs INTEGER NOT NULL,
    cb_startdate DATE NOT NULL,
    cb_enddate DATE NOT NULL,
    cb_computedat TIMESTAMPTZ NOT NULL,
    CONSTRAINT pk_cb PRIMARY KEY (cb_id),
    CONSTRAINT uq_cb UNIQUE (sensor_id, cb_dayofweek, cb_hourofday, cb_computedat),
    CONSTRAINT chk_cb_dayofweek CHECK (cb_dayofweek BETWEEN 0 AND 6),
    CONSTRAINT chk_cb_hourofday CHECK (cb_hourofday BETWEEN 0 AND 23)
);

ALTER TABLE crowd_baseline 
ADD CONSTRAINT fk_cb_sensor FOREIGN KEY (sensor_id) REFERENCES sensor(sensor_id);

CREATE TABLE sensor_hourly_count (
    sc_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sensor_id INTEGER NOT NULL,
    sc_date DATE NOT NULL,
    sc_hour INTEGER NOT NULL,
    sc_dir1 INTEGER,
    sc_dir2 INTEGER,
    sc_totaldirs INTEGER,
    sc_addedat TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_sc UNIQUE (sensor_id, sc_date, sc_hour)
);

ALTER TABLE sensor_hourly_count 
ADD CONSTRAINT fk_sc_sensor FOREIGN KEY (sensor_id) REFERENCES sensor(sensor_id);

CREATE OR REPLACE VIEW latest_pedestrian_status AS
SELECT
    s.sensor_id,
    sc.sc_date,
    sc.sc_hour,
    sc.sc_dir1,
    sc.sc_dir2,
    sc.sc_totaldirs,
    sc.sc_addedat,
    cb.cb_dir1,
    cb.cb_dir2,
    cb.cb_totaldirs,
    cb.cb_startdate,
    cb.cb_enddate,
    cb.cb_computedat,
    CASE
        WHEN cb.cb_totaldirs IS NULL THEN NULL
        ELSE ROUND(
            sc.sc_totaldirs::numeric / NULLIF(cb.cb_totaldirs, 0),
            4
        )
    END AS ratio,
    CASE
        WHEN cb.cb_totaldirs IS NULL THEN 'unknown'
        WHEN sc.sc_totaldirs::numeric / NULLIF(cb.cb_totaldirs, 0) < 0.85
            THEN 'quiet'
        WHEN sc.sc_totaldirs::numeric / NULLIF(cb.cb_totaldirs, 0) < 1.20
            THEN 'typical'
        WHEN sc.sc_totaldirs::numeric / NULLIF(cb.cb_totaldirs, 0) < 1.40
            THEN 'busy'
        ELSE 'crowded'
    END AS band
FROM 
	sensor s
	LEFT JOIN LATERAL
(
    SELECT DISTINCT ON (sensor_id)
        sensor_id,
        sc_date,
        sc_hour,
        sc_dir1,
        sc_dir2,
        sc_totaldirs,
        sc_addedat
    FROM sensor_hourly_count
    ORDER BY
        sensor_id,
        sc_date DESC,
        sc_hour DESC,
        sc_addedat DESC
) AS sc ON s.sensor_id = sc.sensor_id
LEFT JOIN LATERAL (
    SELECT
        cb_id,
        cb_dayofweek,
        cb_hourofday,
        cb_dir1,
        cb_dir2,
        cb_totaldirs,
        cb_startdate,
        cb_enddate,
        cb_computedat
    FROM crowd_baseline
    WHERE crowd_baseline.sensor_id = sc.sensor_id
      AND crowd_baseline.cb_dayofweek =
            EXTRACT(DOW FROM sc.sc_date)::integer
      AND crowd_baseline.cb_hourofday = sc.sc_hour
    ORDER BY cb_computedat DESC
    LIMIT 1
) AS cb ON TRUE;

drop table if exists raw_sensor_count;

create table raw_sensor_count (
	id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	location_id INTEGER NOT NULL,
    sensing_datetime TIMESTAMPTZ NOT NULL,
    sensing_date DATE NOT NULL,
    sensing_time VARCHAR(10) NOT NULL,
    direction_1 INTEGER,
    direction_2 INTEGER,
    total_of_directions INTEGER,
    retrieved_at TIMESTAMPTZ NOT NULL,
	constraint uq_rsc unique (location_id, sensing_datetime)
);

drop table if exists sc_ingestion_run;
create table sc_ingestion_run (
	id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    last_successful_retrieval timestamptz,
    last_processed_hour timestamptz
);