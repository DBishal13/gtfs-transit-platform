-- Builds shape_geom (LineString per shape_id) and stop_geom (Point per stop)
-- for one feed after its raw CSVs have been loaded via load.py.
--
-- Usage: psql -U transit -d transit -v feed_id="'broward-bct'" -f pipeline/postgis/geometries.sql

INSERT INTO shape_geoms (feed_id, shape_id, shape_geom)
SELECT
  feed_id,
  shape_id,
  ST_MakeLine(ST_SetSRID(ST_MakePoint(shape_pt_lon, shape_pt_lat), 4326) ORDER BY shape_pt_sequence)
FROM shapes
WHERE feed_id = :feed_id
GROUP BY feed_id, shape_id
ON CONFLICT (feed_id, shape_id) DO UPDATE SET shape_geom = EXCLUDED.shape_geom;

UPDATE stops
SET stop_geom = ST_SetSRID(ST_MakePoint(stop_lon, stop_lat), 4326)
WHERE feed_id = :feed_id
  AND stop_lon IS NOT NULL
  AND stop_lat IS NOT NULL;

-- Convenience views the QGIS / deep-dive track connects to directly.
CREATE OR REPLACE VIEW stops_view AS
SELECT feed_id, stop_id, stop_name, stop_code, wheelchair_boarding, stop_geom
FROM stops
WHERE stop_geom IS NOT NULL;

CREATE OR REPLACE VIEW shape_geoms_view AS
SELECT sg.feed_id, sg.shape_id, r.route_id, r.route_short_name, r.route_long_name, sg.shape_geom
FROM shape_geoms sg
JOIN trips t ON t.feed_id = sg.feed_id AND t.shape_id = sg.shape_id
JOIN routes r ON r.feed_id = t.feed_id AND r.route_id = t.route_id
GROUP BY sg.feed_id, sg.shape_id, r.route_id, r.route_short_name, r.route_long_name, sg.shape_geom;
