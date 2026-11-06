select index_id, weight_period, weight_pct
from (
    select
        index_id,
        weight_period,
        weight_pct,
        row_number() over (partition by index_id order by weight_period desc) as recency
    from {{ ref('stg_weights') }}
) ranked
where recency = 1
