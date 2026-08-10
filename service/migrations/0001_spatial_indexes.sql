-- GIST spatial indexes on the geometry columns pipeline/postgis/schema.sql already defines
-- (stops.stop_geom, shape_geoms.shape_geom) but never indexed. Required for the KNN (<->)
-- and ST_DWithin queries in service/app/services/geo_service.py to run efficiently at
-- more-than-toy feed sizes.

CREATE INDEX IF NOT EXISTS stops_geom_gist ON stops USING GIST (stop_geom);
CREATE INDEX IF NOT EXISTS shape_geoms_geom_gist ON shape_geoms USING GIST (shape_geom);
