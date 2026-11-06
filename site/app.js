const data = window.BRIEFING;

function fillText(id, value) {
  const node = document.getElementById(id);
  if (node) node.textContent = value;
}

function colorFor(value) {
  if (value >= 8) return "#9d2c2c";
  if (value >= 4) return "#8a5a00";
  if (value < 0) return "#1d6b45";
  return "#1d4e89";
}

function renderKpis() {
  const root = document.getElementById("kpis");
  root.innerHTML = data.kpis
    .map(
      (card) => `
      <article class="card ${card.tone}">
        <span>${card.label}</span>
        <strong>${card.value}</strong>
        <p>${card.detail}</p>
      </article>`,
    )
    .join("");
}

function renderSwaps() {
  document.getElementById("swaps").innerHTML = data.swaps
    .map(
      (swap) => `
      <article class="swap">
        <h3>${swap.item}</h3>
        <p>${swap.change} on a year ago.</p>
        <ul>
          ${swap.alternatives
            .map((item) => `<li>${item.name}, ${item.change}</li>`)
            .join("")}
        </ul>
      </article>`,
    )
    .join("");
}

function renderQuestions() {
  document.getElementById("questions").innerHTML = data.qa
    .map(
      (item, index) => `
      <details ${index === 0 ? "open" : ""}>
        <summary>${item.question}</summary>
        <p>${item.answer}</p>
        <ul class="checked">
          ${item.checked.map((line) => `<li>${line}</li>`).join("")}
        </ul>
      </details>`,
    )
    .join("");
}

function renderSources() {
  document.getElementById("sources").innerHTML = data.sources
    .map(
      (source) =>
        `<li><a href="${source.url}">${source.publisher}</a> — ${source.name}. ${source.licence}.</li>`,
    )
    .join("");
}

function heroChart() {
  const chart = echarts.init(document.getElementById("hero-chart"));
  const rows = data.hero.rows;
  chart.setOption({
    grid: { left: 150, right: 64, top: 10, bottom: 24 },
    tooltip: { trigger: "item", formatter: (item) => `${item.name}: ${item.value}%` },
    xAxis: {
      type: "value",
      axisLabel: { formatter: "{value}%" },
      splitLine: { lineStyle: { color: "#eadfcd" } },
    },
    yAxis: {
      type: "category",
      inverse: true,
      data: rows.map((row) => row.name),
      axisTick: { show: false },
      axisLine: { show: false },
    },
    series: [
      {
        type: "bar",
        data: rows.map((row) => ({
          value: row.yoy,
          itemStyle: { color: colorFor(row.yoy), borderRadius: 4 },
        })),
        label: {
          show: true,
          position: "right",
          formatter: (item) => `${Number(item.value).toFixed(1)}%`,
          color: "#1c1915",
        },
        barWidth: 16,
      },
    ],
  });
  return chart;
}

function pathChart() {
  const chart = echarts.init(document.getElementById("path-chart"));
  const palette = ["#9d2c2c", "#8a5a00", "#1d4e89", "#1d6b45", "#6d6458"];
  chart.setOption({
    color: palette,
    grid: { left: 48, right: 16, top: 36, bottom: 32 },
    tooltip: { trigger: "axis" },
    legend: { top: 0 },
    xAxis: { type: "category", data: data.paths.labels, axisTick: { show: false } },
    yAxis: { type: "value", axisLabel: { formatter: "{value}%" }, splitLine: { lineStyle: { color: "#eadfcd" } } },
    series: data.paths.series.map((series) => ({
      name: series.name,
      type: "line",
      data: series.values,
      showSymbol: false,
      lineStyle: { width: 3 },
    })),
  });
  return chart;
}

function contextChart() {
  const chart = echarts.init(document.getElementById("context-chart"));
  const rows = data.context.rows;
  chart.setOption({
    grid: { left: 120, right: 72, top: 10, bottom: 24 },
    tooltip: {
      trigger: "item",
      formatter: (item) => {
        const row = rows[item.dataIndex];
        return `${row.name}<br>${row.yoy}% on a year ago<br>Added ${row.points} points`;
      },
    },
    xAxis: { type: "value", axisLabel: { formatter: "{value}%" }, splitLine: { lineStyle: { color: "#eadfcd" } } },
    yAxis: {
      type: "category",
      inverse: true,
      data: rows.map((row) => row.name),
      axisTick: { show: false },
      axisLine: { show: false },
    },
    series: [
      {
        type: "bar",
        data: rows.map((row) => ({
          value: row.yoy,
          itemStyle: { color: colorFor(row.yoy), borderRadius: 4 },
        })),
        label: {
          show: true,
          position: "right",
          formatter: (item) => `${Number(item.value).toFixed(1)}%`,
          color: "#1c1915",
        },
        barWidth: 18,
      },
    ],
  });
  return chart;
}

function rateChart() {
  const chart = echarts.init(document.getElementById("rate-chart"));
  const hikes = new Set(data.cash_rate.hikes.map((hike) => hike.date));
  chart.setOption({
    grid: { left: 48, right: 16, top: 20, bottom: 32 },
    tooltip: { trigger: "axis", formatter: (items) => `${items[0].axisValue}<br>${items[0].data}%` },
    xAxis: {
      type: "category",
      data: data.cash_rate.points.map((point) => point.date),
      axisLabel: { hideOverlap: true },
    },
    yAxis: {
      type: "value",
      min: 3.4,
      max: 5.0,
      interval: 0.2,
      axisLabel: { formatter: (value) => `${value.toFixed(1)}%` },
    },
    series: [
      {
        type: "line",
        step: "end",
        showSymbol: false,
        data: data.cash_rate.points.map((point) => point.rate),
        lineStyle: { width: 3, color: "#9d2c2c" },
        markPoint: {
          symbol: "circle",
          symbolSize: 14,
          label: { show: false },
          itemStyle: { color: "#1c1915" },
          data: data.cash_rate.points
            .map((point, index) => (hikes.has(point.date) ? { coord: [index, point.rate] } : null))
            .filter(Boolean),
        },
      },
    ],
  });
  return chart;
}

const HASH_TO_PANEL = {
  "": "panel-briefing",
  "#month": "panel-briefing",
  "#shop": "panel-shop",
  "#swaps": "panel-swaps",
  "#watch": "panel-watch",
  "#questions": "panel-questions",
};

function showPanel(panelId, charts) {
  const buttons = [...document.querySelectorAll(".tabs button")];
  buttons.forEach((button) => {
    button.setAttribute("aria-selected", String(button.dataset.panel === panelId));
  });
  document.querySelectorAll(".panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === panelId);
  });
  charts.forEach((chart) => chart.resize());
}

function setupTabs(charts) {
  const buttons = [...document.querySelectorAll(".tabs button")];
  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const hash = {
        "panel-briefing": "#month",
        "panel-shop": "#shop",
        "panel-swaps": "#swaps",
        "panel-watch": "#watch",
        "panel-questions": "#questions",
      }[button.dataset.panel];
      if (location.hash !== hash) {
        location.hash = hash;
      } else {
        showPanel(button.dataset.panel, charts);
      }
    });
  });
  window.addEventListener("hashchange", () => {
    showPanel(HASH_TO_PANEL[location.hash] || "panel-briefing", charts);
  });
  showPanel(HASH_TO_PANEL[location.hash] || "panel-briefing", charts);
}

fillText("lede", data.lede);
fillText("prepared", `Prepared ${data.prepared_label}. Figures are for ${data.period_label}.`);
fillText("hero-title", data.hero.title);
fillText("hero-note", data.hero.note);
fillText("path-title", data.paths.title);
fillText("path-note", data.paths.note);
fillText("context-title", data.context.title);
fillText("context-note", data.context.note);
document.getElementById("context-points").innerHTML = data.context.rows
  .map(
    (row) =>
      `<li>${row.name}: ${row.yoy.toFixed(1)}% on a year ago, added ${row.points.toFixed(2)} points</li>`,
  )
  .join("");
fillText("rate-title", data.cash_rate.title);
fillText("rate-note", data.cash_rate.note);
fillText("means", data.means);
renderKpis();
renderSwaps();
renderQuestions();
renderSources();

const charts = [heroChart(), pathChart(), contextChart(), rateChart()];
setupTabs(charts);
window.addEventListener("resize", () => charts.forEach((chart) => chart.resize()));
