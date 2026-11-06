select
    index_id,
    abs_name,
    plain_name,
    level,
    family,
    cast(shelf as integer) as shelf,
    aisle
from {{ ref('series_catalog') }}
