select
    index_id,
    period,
    cast(value as double) as contribution_pp
from {{ source('bronze', 'cpi_observations') }}
where measure = '7'
