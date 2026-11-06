-- Published yearly percent change should match the change calculated from the
-- index, within rounding. Rows returned here fail the build.
select
    index_id,
    period,
    yoy_pct,
    yoy_from_index_pct
from {{ ref('mart_category_monthly') }}
where yoy_pct is not null
  and yoy_from_index_pct is not null
  and abs(yoy_pct - yoy_from_index_pct) > 0.15
