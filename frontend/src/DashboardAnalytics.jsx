
export default function DashboardAnalytics({ summary = {}, employees = [], offices = [] }) {
  const total = Number(summary.total_employees ?? employees.length) || 0;
  const present = Number(summary.present) || 0;
  const late = Number(summary.late) || 0;
  const absent = Number(summary.absent) || 0;
  const attendanceTotal = present + late + absent;
  const attendanceRate = total
    ? Math.round(((present + late) / total) * 100)
    : 0;

  const activeOffices = offices.filter(office => office.is_active).length;

  const departmentMap = {};
  employees.forEach(employee => {
    const department = employee.department?.trim() || "Unassigned";
    departmentMap[department] = (departmentMap[department] || 0) + 1;
  });

  const departments = Object.entries(departmentMap)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  const maxDepartment = Math.max(...departments.map(item => item[1]), 1);

  const cardStyle = {
    background: "var(--analytics-card, #fff)",
    border: "1px solid var(--analytics-border, #e9edf5)",
    borderRadius: "18px",
    padding: "22px",
    minWidth: 0
  };

  const muted = {
    color: "var(--analytics-muted, #8290a5)",
    fontSize: "13px"
  };

  return (
    <section className="analytics-section">
      <div className="analytics-heading">
        <div>
          <h3>Workforce Analytics</h3>
          <p>Organization performance at a glance</p>
        </div>
        <span className="analytics-live"><span /> LIVE OVERVIEW</span>
      </div>

      <div className="analytics-grid">
        <div style={cardStyle} className="analytics-card">
          <div className="analytics-card-heading">
            <div>
              <span style={muted}>Attendance Rate</span>
              <h2>{attendanceRate}%</h2>
            </div>
            <div className="analytics-icon blue">◉</div>
          </div>
          <div className="analytics-progress">
            <div style={{ width: `${Math.min(attendanceRate, 100)}%` }} />
          </div>
          <p style={muted}>{present + late} out of {total} employees marked present or late</p>
        </div>

        <div style={cardStyle} className="analytics-card">
          <div className="analytics-card-heading">
            <div>
              <span style={muted}>Active Offices</span>
              <h2>{activeOffices}</h2>
            </div>
            <div className="analytics-icon purple">⌖</div>
          </div>
          <p style={muted}>{offices.length} registered offices</p>
          <div className="analytics-office-indicator">
            <span /> {activeOffices} operational terminals
          </div>
        </div>

        <div style={cardStyle} className="analytics-card analytics-wide">
          <div className="analytics-card-heading">
            <div>
              <h3>Today's Attendance</h3>
              <p style={muted}>Employee attendance breakdown</p>
            </div>
          </div>

          <div className="attendance-chart-layout">
            <div
              className="attendance-donut"
              style={{
                background: attendanceTotal
                  ? `conic-gradient(#16a879 0% ${present / attendanceTotal * 100}%, #e9a23b ${present / attendanceTotal * 100}% ${(present + late) / attendanceTotal * 100}%, #e35d6a ${(present + late) / attendanceTotal * 100}% 100%)`
                  : "#e9edf5"
              }}
            >
              <div className="donut-center">
                <strong>{attendanceTotal}</strong>
                <span>Records</span>
              </div>
            </div>

            <div className="attendance-legend">
              <div><span className="legend-dot" style={{ background: "#16a879" }} />Present<strong>{present}</strong></div>
              <div><span className="legend-dot" style={{ background: "#e9a23b" }} />Late<strong>{late}</strong></div>
              <div><span className="legend-dot" style={{ background: "#e35d6a" }} />Absent<strong>{absent}</strong></div>
            </div>
          </div>
        </div>

        <div style={cardStyle} className="analytics-card analytics-wide">
          <div className="analytics-card-heading">
            <div>
              <h3>Department Overview</h3>
              <p style={muted}>Employees across departments</p>
            </div>
            <span className="analytics-total">{employees.length} Total</span>
          </div>

          {departments.length ? (
            <div className="department-chart">
              {departments.map(([name, count]) => (
                <div className="department-row" key={name}>
                  <div className="department-label">
                    <span title={name}>{name}</span>
                    <strong>{count}</strong>
                  </div>
                  <div className="department-track">
                    <div style={{ width: `${count / maxDepartment * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="analytics-empty">Add employees with department details to see this chart.</div>
          )}
        </div>
      </div>
    </section>
  );
}
