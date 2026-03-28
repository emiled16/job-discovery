function maxCount(series) {
  return series.reduce((highest, item) => Math.max(highest, item.count), 0);
}

export function SummaryChart({ series, bucket }) {
  if (!series.length) {
    return (
      <section className="empty-panel compact-panel">
        <p className="eyebrow">No activity</p>
        <h2>No tracked applications in the selected range.</h2>
        <p>Once you start marking roles as applied, the trend chart will populate here.</p>
      </section>
    );
  }

  const highest = Math.max(maxCount(series), 1);

  return (
    <section className="chart-panel">
      <div className="chart-header">
        <div>
          <p className="eyebrow">Trend</p>
          <h2>Applications over time</h2>
        </div>
        <span className="metric-chip">{bucket === "week" ? "Weekly buckets" : "Daily buckets"}</span>
      </div>

      <div className="trend-chart" aria-label="Applications over time">
        {series.map((point) => (
          <div key={point.bucket_start} className="trend-column">
            <div
              className="trend-bar"
              style={{ height: `${Math.max((point.count / highest) * 100, point.count ? 12 : 2)}%` }}
              title={`${point.bucket_start}: ${point.count}`}
            />
            <strong>{point.count}</strong>
            <span>{point.bucket_start}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
