CREATE TABLE IF NOT EXISTS place (
    place_id INTEGER GENERATED ALWAYS AS IDENTITY,
    place_cat VARCHAR(30) NOT NULL,
    place_name TEXT NOT NULL,
    place_address TEXT,
    place_lat DOUBLE PRECISION NOT NULL,
    place_lon DOUBLE PRECISION NOT NULL,
    place_detailsjson TEXT,
    place_src VARCHAR(50) NOT NULL,
    place_srcassetid TEXT NOT NULL,
    place_active BOOLEAN NOT NULL DEFAULT TRUE,
    place_importedat TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_place PRIMARY KEY (place_id),

    CONSTRAINT chk_place_cat CHECK (
        place_cat IN ('food_venue', 'museum_gallery')
    ),

    CONSTRAINT chk_place_lat CHECK (
        place_lat BETWEEN -90 AND 90
    ),

    CONSTRAINT chk_place_lon CHECK (
        place_lon BETWEEN -180 AND 180
    ),

    CONSTRAINT uq_place_source UNIQUE (
        place_src,
        place_srcassetid
    )
);

CREATE INDEX IF NOT EXISTS idx_place_cat
ON place(place_cat);

CREATE INDEX IF NOT EXISTS idx_place_active_cat
ON place(place_active, place_cat);

CREATE INDEX IF NOT EXISTS idx_place_coordinates
ON place(place_lat, place_lon);