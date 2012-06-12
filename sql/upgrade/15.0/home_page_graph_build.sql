\set ON_ERROR_STOP 1

-- create new table for home page graph

SELECT create_table_if_not_exists('home_page_graph',
$t$
CREATE TABLE home_page_graph_build_data (
  product_version_id int not null,
  report_date date not null,
  build_date date not null,
  report_count int not null default 0,
  adu int not null default 0,
  constraint home_page_graph_key primary key ( product_version_id, report_date )
);$t$, 'breakpad_rw' );

-- create view

CREATE OR REPLACE VIEW home_page_graph_build_view
AS
SELECT product_version_id,
  product_name,
  version_string,
  build_date,
  sum(report_count) as report_count,
  sum(adu) as adu,
  ( sum(report_count) * throttle * 100 ) / sum(adu) as crash_hadu
FROM home_page_graph_build
  JOIN product_versions USING (product_version_id)
  JOIN product_release_channels ON
       product_versions.product_name = product_release_channels.product_name
          AND product_versions.build_type = product_release_channels.release_channel;

-- daily update function
CREATE OR REPLACE FUNCTION update_home_page_graph_build (
    updateday DATE, 
    checkdata BOOLEAN default TRUE,
    check_period INTERVAL default interval '1 hour' )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET work_mem = '512MB'
SET temp_buffers = '512MB'
SET client_min_messages = 'ERROR'
SET timezone = 'UTC'
AS $f$
BEGIN

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM home_page_graph_build
    WHERE report_date = updateday
    LIMIT 1;
    IF FOUND THEN
        RAISE NOTICE 'home_page_graph has already been run for %.',updateday;
        RETURN FALSE;
    END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
    IF checkdata THEN
        RAISE EXCEPTION 'Reports_clean has not been updated to the end of %',updateday;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- check for product_adu

PERFORM 1 FROM product_adu
WHERE adu_date = updateday
LIMIT 1;
IF NOT FOUND THEN
  IF checkdata THEN
    RAISE EXCEPTION 'product_adu has not been updated for %', updateday;
  ELSE
    RETURN FALSE;
  END IF;
END IF;

-- now insert the new records
INSERT INTO home_page_graph_build 
    ( product_version_id, build_date, report_date 
      report_count, adu )
SELECT product_version_id, build_date, updateday
    report_count, adu_sum
FROM ( select product_version_id, 
            count(*) as report_count,
            build_date(build_id) as build_date
      FROM reports_clean
      WHERE 
          AND date_processed >= updateday::timestamptz
          AND date_processed < ( updateday + 1 )::timestamptz
          -- only 7 days of each build
          AND build_date(build_id) >= ( updateday + 7 )
          -- exclude browser hangs from total counts 
          AND NOT ( process_type = 'browser' and hang_id IS NOT NULL )
      group by product_version_id, build_date(build_id) ) as count_reports
      JOIN
    ( select product_version_id,
        sum(adu_count) as adu_sum,
        build_date
        from build_adu
        where adu_date = updateday
        group by product_version_id, build_date ) as sum_adu
      USING ( product_version_id, build_date )
      JOIN product_versions USING ( product_version_id )
      JOIN product_release_channels ON
          product_versions.product_name = product_release_channels.product_name
          AND product_versions.build_type = product_release_channels.release_channel
WHERE sunset_date > ( current_date - interval '1 year' )
ORDER BY product_version_id;

RETURN TRUE;
END; $f$;

-- now create a backfill function 
-- so that we can backfill missing data
CREATE OR REPLACE FUNCTION backfill_home_page_graph_build(
    updateday DATE, check_period INTERVAL DEFAULT INTERVAL '1 hour' )
RETURNS BOOLEAN
LANGUAGE plpgsql AS
$f$
BEGIN

DELETE FROM home_page_graph_build WHERE report_date = updateday;
PERFORM update_home_page_graph_build(updateday, false, check_period);

RETURN TRUE;
END; $f$;


-- sample backfill script
-- for initialization
DO $f$
DECLARE 
    thisday DATE := ( current_date - 7 );
    lastday DATE;
BEGIN

    -- set backfill to the last day we have ADU for
    SELECT max("date") 
    INTO lastday
    FROM product_adu;
    
    WHILE thisday <= lastday LOOP
    
        RAISE INFO 'backfilling %', thisday;
    
        PERFORM backfill_home_page_graph_build(thisday);
        
        thisday := thisday + 1;
        
    END LOOP;
    
END;$f$;

