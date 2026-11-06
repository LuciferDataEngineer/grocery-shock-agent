select
    index_id,
    index_name,
    period as weight_period,
    cast(weight_pct as double) as weight_pct
from {{ source('bronze', 'cpi_weights') }}
where weight_pct is not null
