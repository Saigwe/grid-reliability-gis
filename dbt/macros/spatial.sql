{# Spatial SQL that builds on DuckDB (spatial extension) and on PostGIS. Distances are planar metres in British
   National Grid (EPSG:27700), the right projection for Great Britain. #}

{% macro wgs84_point(lon, lat) %}{{ return(adapter.dispatch('wgs84_point')(lon, lat)) }}{% endmacro %}
{% macro duckdb__wgs84_point(lon, lat) %}ST_Point({{ lon }}, {{ lat }}){% endmacro %}
{% macro default__wgs84_point(lon, lat) %}ST_SetSRID(ST_MakePoint({{ lon }}, {{ lat }}), 4326){% endmacro %}

{% macro wgs84_from_wkt(wkt) %}{{ return(adapter.dispatch('wgs84_from_wkt')(wkt)) }}{% endmacro %}
{% macro duckdb__wgs84_from_wkt(wkt) %}ST_GeomFromText({{ wkt }}){% endmacro %}
{% macro default__wgs84_from_wkt(wkt) %}ST_GeomFromText({{ wkt }}, 4326){% endmacro %}

{% macro to_bng(geom) %}{{ return(adapter.dispatch('to_bng')(geom)) }}{% endmacro %}
{% macro duckdb__to_bng(geom) %}ST_Transform({{ geom }}, 'EPSG:4326', 'EPSG:27700', true){% endmacro %}
{% macro default__to_bng(geom) %}ST_Transform({{ geom }}, 27700){% endmacro %}

{# Length of a WGS84 geometry in metres. #}
{% macro length_m(geom) %}ST_Length({{ to_bng(geom) }}){% endmacro %}

{# Minutes between two timestamps. #}
{% macro minutes_between(start, end) %}cast((extract(epoch from {{ end }}) - extract(epoch from {{ start }})) / 60.0 as double precision){% endmacro %}
