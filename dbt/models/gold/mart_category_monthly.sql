with lagged as (
    select
        index_id,
        index_name,
        period,
        index_value,
        lag(index_value) over (partition by index_id order by period) as prior_month_index,
        lag(index_value, 12) over (partition by index_id order by period) as prior_year_index
    from {{ ref('stg_cpi_index') }}
)

select
    lagged.index_id,
    lagged.index_id || '|' || lagged.period as series_month_key,
    coalesce(catalog.plain_name, lagged.index_name) as plain_name,
    lagged.index_name as abs_name,
    catalog.level,
    catalog.family,
    coalesce(catalog.shelf, 0) as shelf,
    catalog.aisle,
    lagged.period,
    lagged.index_value,
    case
        when lagged.prior_month_index is null or lagged.prior_month_index = 0 then null
        else (lagged.index_value / lagged.prior_month_index - 1) * 100
    end as mom_pct,
    case
        when lagged.prior_year_index is null or lagged.prior_year_index = 0 then null
        else (lagged.index_value / lagged.prior_year_index - 1) * 100
    end as yoy_from_index_pct,
    yoy.yoy_pct,
    contribution.contribution_pp,
    weights.weight_pct,
    weights.weight_period
from lagged
left join {{ ref('stg_cpi_yoy') }} as yoy
    on lagged.index_id = yoy.index_id
    and lagged.period = yoy.period
left join {{ ref('stg_cpi_contribution') }} as contribution
    on lagged.index_id = contribution.index_id
    and lagged.period = contribution.period
left join {{ ref('stg_catalog') }} as catalog
    on lagged.index_id = catalog.index_id
left join {{ ref('stg_weight_latest') }} as weights
    on lagged.index_id = weights.index_id
