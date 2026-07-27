-- PostGIS schema for the local "deep-dive" track: hands-on SQL/spatial analysis
-- against one or more GTFS feeds loaded side by side. This is the multi-agency,
-- feed-parameterized evolution of the original single-feed schema this project
-- started with — every table now carries a `feed_id` so Broward County Transit
-- and any other agency's feed can coexist in one database without id collisions.
--
-- Run automatically by docker-compose (mounted into /docker-entrypoint-initdb.d),
-- or manually via: psql -U transit -d transit -f pipeline/postgis/schema.sql

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS feeds (
  feed_id text PRIMARY KEY,
  name text NOT NULL,
  region text,
  source_url text,
  license text
);

CREATE TABLE IF NOT EXISTS agency (
  feed_id text NOT NULL REFERENCES feeds(feed_id) ON DELETE CASCADE,
  agency_id text NOT NULL DEFAULT '',
  agency_name text,
  agency_url text,
  agency_timezone text,
  agency_lang text,
  agency_phone text,
  PRIMARY KEY (feed_id, agency_id)
);

CREATE TABLE IF NOT EXISTS calendar (
  feed_id text NOT NULL REFERENCES feeds(feed_id) ON DELETE CASCADE,
  service_id text NOT NULL,
  monday int NOT NULL,
  tuesday int NOT NULL,
  wednesday int NOT NULL,
  thursday int NOT NULL,
  friday int NOT NULL,
  saturday int NOT NULL,
  sunday int NOT NULL,
  start_date date NOT NULL,
  end_date date NOT NULL,
  PRIMARY KEY (feed_id, service_id)
);

CREATE TABLE IF NOT EXISTS exception_types (
  exception_type int PRIMARY KEY,
  description text
);

CREATE TABLE IF NOT EXISTS calendar_dates (
  feed_id text NOT NULL REFERENCES feeds(feed_id) ON DELETE CASCADE,
  service_id text NOT NULL,
  date date NOT NULL,
  exception_type int REFERENCES exception_types(exception_type)
);
CREATE INDEX IF NOT EXISTS calendar_dates_dateidx ON calendar_dates (feed_id, date);

CREATE TABLE IF NOT EXISTS routes (
  feed_id text NOT NULL REFERENCES feeds(feed_id) ON DELETE CASCADE,
  route_id text NOT NULL,
  route_short_name text DEFAULT '',
  route_long_name text DEFAULT '',
  route_desc text DEFAULT '',
  route_type int,
  route_url text,
  route_color text,
  route_text_color text,
  PRIMARY KEY (feed_id, route_id)
);

CREATE TABLE IF NOT EXISTS shapes (
  feed_id text NOT NULL REFERENCES feeds(feed_id) ON DELETE CASCADE,
  shape_id text NOT NULL,
  shape_pt_lat double precision NOT NULL,
  shape_pt_lon double precision NOT NULL,
  shape_pt_sequence int NOT NULL
);
CREATE INDEX IF NOT EXISTS shapes_shape_key ON shapes (feed_id, shape_id);

-- Populated by geometries.sql once shapes.txt has been loaded.
CREATE TABLE IF NOT EXISTS shape_geoms (
  feed_id text NOT NULL REFERENCES feeds(feed_id) ON DELETE CASCADE,
  shape_id text NOT NULL,
  shape_geom geometry ('LINESTRING', 4326),
  PRIMARY KEY (feed_id, shape_id)
);

CREATE TABLE IF NOT EXISTS location_types (
  location_type int PRIMARY KEY,
  description text
);

CREATE TABLE IF NOT EXISTS stops (
  feed_id text NOT NULL REFERENCES feeds(feed_id) ON DELETE CASCADE,
  stop_id text NOT NULL,
  stop_code text,
  stop_name text,
  stop_desc text,
  stop_lat double precision,
  stop_lon double precision,
  zone_id text,
  stop_url text,
  location_type integer REFERENCES location_types(location_type),
  parent_station text,
  stop_geom geometry ('POINT', 4326),
  wheelchair_boarding int,
  PRIMARY KEY (feed_id, stop_id)
);

CREATE TABLE IF NOT EXISTS pickup_dropoff_types (
  type_id int PRIMARY KEY,
  description text
);

CREATE TABLE IF NOT EXISTS trips (
  feed_id text NOT NULL REFERENCES feeds(feed_id) ON DELETE CASCADE,
  route_id text NOT NULL,
  service_id text NOT NULL,
  trip_id text NOT NULL,
  trip_headsign text,
  direction_id int,
  block_id text,
  shape_id text,
  PRIMARY KEY (feed_id, trip_id)
);
CREATE INDEX IF NOT EXISTS trips_route_idx ON trips (feed_id, route_id);

CREATE TABLE IF NOT EXISTS stop_times (
  feed_id text NOT NULL REFERENCES feeds(feed_id) ON DELETE CASCADE,
  trip_id text NOT NULL,
  -- Stored as text, not interval: GTFS times can exceed 24:00:00 for trips past
  -- midnight, which `interval` handles fine, but keeping the raw string avoids
  -- surprises during \copy and lets pipeline.utils.time do the parsing uniformly
  -- with the Python analytics path.
  arrival_time text,
  departure_time text,
  stop_id text NOT NULL,
  stop_sequence int NOT NULL,
  pickup_type int REFERENCES pickup_dropoff_types(type_id),
  drop_off_type int REFERENCES pickup_dropoff_types(type_id),
  shape_dist_traveled double precision,
  PRIMARY KEY (feed_id, trip_id, stop_sequence)
);
CREATE INDEX IF NOT EXISTS stop_times_key ON stop_times (feed_id, trip_id, stop_id);

INSERT INTO exception_types (exception_type, description) VALUES
(1, 'service has been added'),
(2, 'service has been removed')
ON CONFLICT DO NOTHING;

INSERT INTO location_types (location_type, description) VALUES
(0, 'stop'),
(1, 'station'),
(2, 'station entrance')
ON CONFLICT DO NOTHING;

INSERT INTO pickup_dropoff_types (type_id, description) VALUES
(0, 'Regularly Scheduled'),
(1, 'Not available'),
(2, 'Phone arrangement only'),
(3, 'Driver arrangement only')
ON CONFLICT DO NOTHING;
