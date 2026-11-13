// Draws the three dashboard charts from data the template puts in window.SPENDWISE
(function () {
  if (!window.Chart || !window.SPENDWISE) return;
  const data = window.SPENDWISE;
  const money = (v) => data.currency + Number(v).toLocaleString("en-IN", { maximumFractionDigits: 0 });
  const palette = ["#4f46e5", "#0f9d6b", "#e3a008", "#d6455d", "#0ea5e9", "#8b5cf6", "#f97316", "#64748b", "#14b8a6", "#ec4899"];
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  Chart.defaults.color = "#6b7489";

  const cat = document.getElementById("categoryChart");
  if (cat) {
    new Chart(cat, {
      type: "doughnut",
      data: { labels: data.category.labels, datasets: [{ data: data.category.values, backgroundColor: palette, borderWidth: 2 }] },
      options: {
        maintainAspectRatio: false, cutout: "62%",
        plugins: {
          legend: { position: "right" },
          tooltip: { callbacks: { label: (c) => `${c.label}: ${money(c.parsed)}` } },
        },
      },
    });
  }

  const daily = document.getElementById("dailyChart");
  if (daily) {
    new Chart(daily, {
      type: "line",
      data: {
        labels: data.daily.labels,
        datasets: [{ label: "Expense", data: data.daily.values, borderColor: "#d6455d", backgroundColor: "rgba(214,69,93,.12)", fill: true, tension: .35, pointRadius: 2 }],
      },
      options: {
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => money(c.parsed.y) } } },
        scales: { y: { beginAtZero: true, ticks: { callback: money } }, x: { grid: { display: false } } },
      },
    });
  }

  const monthly = document.getElementById("monthlyChart");
  if (monthly) {
    new Chart(monthly, {
      type: "line",
      data: {
        labels: data.monthly.labels,
        datasets: [
          { label: "Income", data: data.monthly.income, borderColor: "#0f9d6b", backgroundColor: "#0f9d6b", tension: .3 },
          { label: "Expense", data: data.monthly.expense, borderColor: "#d6455d", backgroundColor: "#d6455d", tension: .3 },
        ],
      },
      options: {
        maintainAspectRatio: false,
        plugins: { tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${money(c.parsed.y)}` } } },
        scales: { y: { beginAtZero: true, ticks: { callback: money } }, x: { grid: { display: false } } },
      },
    });
  }
})();
