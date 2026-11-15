
import { useEffect, useRef, useState } from "react";
import "./App.css";

const API = "https://facetrack-backend-ahlo.onrender.com";

const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

function formatISTTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("en-IN", {
    timeZone: "Asia/Kolkata",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  }).format(date);
}

async function request(path, { token, method = "GET", body } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body && !(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API}${path}`, {
    method,
    headers,
    body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || data.message || `Request failed (${response.status})`);
  }

  return data;
}

function Brand({ light = false }) {
  return (
    <div className={`brand ${light ? "brand-light" : ""}`}>
      <div className="brand-mark">F</div>
      <span>FACE<span className="brand-accent">TRACK</span></span>
    </div>
  );
}

function App() {
  const [page, setPage] = useState("home");
  const [loginMode, setLoginMode] = useState("admin");

  const [session, setSession] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("facetrack_session") || "null");
    } catch {
      return null;
    }
  });

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [organizationId, setOrganizationId] = useState("1");
  const [officeId, setOfficeId] = useState("");
  const [pin, setPin] = useState("");

  // Organization registration
  const [organizationForm, setOrganizationForm] = useState({
    name: "",
    email: "",
    phone: "",
    address: "",
    admin_name: "",
    admin_email: "",
    admin_password: "",
  });

  const [registeredOrganization, setRegisteredOrganization] = useState(null);

  const [employees, setEmployees] = useState([]);
  const [attendance, setAttendance] = useState([]);
  const [summary, setSummary] = useState({});
  const [offices, setOffices] = useState([]);
  const [selectedDate, setSelectedDate] = useState(today());

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [activePage, setActivePage] = useState("overview");

  const [employeeForm, setEmployeeForm] = useState({
    employee_code: "", name: "", email: "", phone: "",
    department: "", designation: "", joining_date: "",
  });

  const [employeePhoto, setEmployeePhoto] = useState(null);
  const [showEmployeeForm, setShowEmployeeForm] = useState(false);

  const [enrollEmployee, setEnrollEmployee] = useState(null);
  const [enrollImage, setEnrollImage] = useState(null);
  const [consent, setConsent] = useState(false);

  const [officeForm, setOfficeForm] = useState({
    device_name: "", location: "", pin: "",
  });

  const [history, setHistory] = useState(null);
  const [scanResult, setScanResult] = useState(null);

  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const fileRef = useRef(null);

  const isAdmin = session?.mode === "admin";
  const isOffice = session?.mode === "office";

  const notify = (text) => {
    setMessage(text);
    setError("");
  };

  const fail = (text) => {
    setError(text);
    setMessage("");
  };

  async function loadDashboard(token, date = selectedDate) {
    const [employeeData, attendanceData, officeData] = await Promise.all([
      request("/employees/", { token }),
      request(`/attendance/records?attendance_date=${date}`, { token }),
      request("/office-devices/", { token }),
    ]);

    setEmployees(employeeData.employees || []);
    setAttendance(attendanceData.records || []);
    setSummary(attendanceData.summary || {});
    setOffices(officeData.offices || []);
  }

  useEffect(() => {
    if (session?.mode === "admin") {
      loadDashboard(session.token).catch((e) => fail(e.message));
    }
  }, [session?.token]);

  useEffect(() => {
    if (session?.mode === "admin") {
      request(`/attendance/records?attendance_date=${selectedDate}`, {
        token: session.token,
      })
        .then((data) => {
          setAttendance(data.records || []);
          setSummary(data.summary || {});
        })
        .catch((e) => fail(e.message));
    }
  }, [selectedDate]);

  useEffect(() => {
    if (!isOffice || page !== "kiosk") return;

    let active = true;

    navigator.mediaDevices?.getUserMedia({
      video: { facingMode: "user" },
      audio: false,
    })
      .then((stream) => {
        if (!active) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
      })
      .catch(() => fail("Camera access nahi mila. Browser permissions check karein."));

    return () => {
      active = false;
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
    };
  }, [isOffice, page]);

  // Register organization and its first admin
  async function handleOrganizationRegister(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setMessage("");

    try {
      const data = await request("/organizations/register-with-admin", {
        method: "POST",
        body: {
          name: organizationForm.name.trim(),
          email: organizationForm.email.trim().toLowerCase(),
          phone: organizationForm.phone.trim() || null,
          address: organizationForm.address.trim() || null,
          admin_name: organizationForm.admin_name.trim(),
          admin_email: organizationForm.admin_email.trim().toLowerCase(),
          admin_password: organizationForm.admin_password,
        },
      });

      setRegisteredOrganization(data);
      setOrganizationId(String(data.organization_id));
      setEmail(organizationForm.admin_email.trim().toLowerCase());
      setPassword("");
      setLoginMode("admin");
      setPage("login");

      setOrganizationForm({
        name: "",
        email: "",
        phone: "",
        address: "",
        admin_name: "",
        admin_email: "",
        admin_password: "",
      });

      notify(
        `Organization created successfully! Your Organization ID is ${data.organization_id}. Please sign in.`
      );
    } catch (e) {
      fail(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleLogin(e) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const path = loginMode === "admin"
        ? "/auth/admin/login"
        : "/auth/office/login";

      const body = loginMode === "admin"
        ? {
            organization_id: Number(organizationId),
            email,
            password,
          }
        : {
            office_id: Number(officeId),
            pin,
          };

      const data = await request(path, { method: "POST", body });

      const nextSession = {
        token: data.access_token,
        mode: loginMode,
        user: loginMode === "admin" ? data.admin : data.office,
      };

      localStorage.setItem("facetrack_session", JSON.stringify(nextSession));
      setSession(nextSession);

      if (loginMode === "office") {
        setPage("kiosk");
      } else {
        setPage("dashboard");
        setActivePage("overview");
        notify("Welcome to FACETRACK.");
      }
    } catch (e) {
      fail(e.message);
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem("facetrack_session");
    setSession(null);
    setPage("home");
    setActivePage("overview");
    setHistory(null);
    setMessage("");
    setError("");
  }

  async function addEmployee(e) {
    e.preventDefault();
    setLoading(true);

    try {
      const form = new FormData();

      Object.entries(employeeForm).forEach(([key, value]) => {
        if (value) form.append(key, value);
      });

      if (employeePhoto) form.append("profile_photo", employeePhoto);

      await request("/employees/add", {
        method: "POST",
        token: session.token,
        body: form,
      });

      setEmployeeForm({
        employee_code: "", name: "", email: "", phone: "",
        department: "", designation: "", joining_date: "",
      });

      setEmployeePhoto(null);
      setShowEmployeeForm(false);

      await loadDashboard(session.token);
      notify("Employee successfully added.");
    } catch (e) {
      fail(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function enrollFace(e) {
    e.preventDefault();

    if (!enrollImage || !consent) {
      fail("Face image select karein aur consent confirm karein.");
      return;
    }

    setLoading(true);

    try {
      const form = new FormData();
      form.append("consent_given", "true");
      form.append("face_image", enrollImage);

      const data = await request(`/face/enroll/${enrollEmployee.id}`, {
        method: "POST",
        token: session.token,
        body: form,
      });

      setEnrollEmployee(null);
      setEnrollImage(null);
      setConsent(false);

      notify(data.message || "Face enrollment successful.");
    } catch (e) {
      fail(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function addOffice(e) {
    e.preventDefault();
    setLoading(true);

    try {
      const params = new URLSearchParams({
        device_name: officeForm.device_name,
        pin: officeForm.pin,
        location: officeForm.location,
      });

      await request(`/office-devices/register?${params.toString()}`, {
        method: "POST",
        token: session.token,
      });

      setOfficeForm({ device_name: "", location: "", pin: "" });

      await loadDashboard(session.token);
      notify("Office kiosk registered successfully.");
    } catch (e) {
      fail(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function deactivateOffice(id) {
    if (!window.confirm("Is office kiosk ko deactivate karna hai?")) return;

    try {
      await request(`/office-devices/${id}/deactivate`, {
        method: "PATCH",
        token: session.token,
      });

      await loadDashboard(session.token);
      notify("Office kiosk deactivated.");
    } catch (e) {
      fail(e.message);
    }
  }

  async function openHistory(employee) {
    setLoading(true);

    try {
      const data = await request(`/attendance/employee/${employee.id}/history`, {
        token: session.token,
      });

      setHistory(data);
    } catch (e) {
      fail(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function scanAttendance() {
    if (!videoRef.current || !streamRef.current) {
      fail("Camera abhi ready nahi hai.");
      return;
    }

    setLoading(true);
    setMessage("");
    setError("");

    try {
      const video = videoRef.current;
      const canvas = document.createElement("canvas");

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      if (!canvas.width || !canvas.height) {
        throw new Error("Camera frame available nahi hai. Dobara try karein.");
      }

      canvas.getContext("2d").drawImage(video, 0, 0);

      const blob = await new Promise((resolve) =>
        canvas.toBlob(resolve, "image/jpeg", 0.9)
      );

      if (!blob) throw new Error("Camera image capture nahi ho payi.");

      const form = new FormData();
      form.append("face_image", blob, "attendance.jpg");

      const data = await request("/attendance/scan", {
        method: "POST",
        token: session.token,
        body: form,
      });

      setScanResult(data);
    } catch (e) {
      setScanResult(null);
      fail(e.message);
    } finally {
      setLoading(false);
    }
  }

  function exportCSV() {
    const headers = [
      "Employee Name", "Employee Code", "Department",
      "Date", "Check In", "Check Out", "Working Minutes", "Status",
    ];

    const rows = attendance.map((r) => [
      r.employee_name, r.employee_code, r.department,
      r.date, r.check_in, r.check_out,
      r.total_working_minutes, r.status,
    ]);

    const csv = [headers, ...rows]
      .map((row) =>
        row.map((v) => `"${String(v ?? "").replaceAll('"', '""')}"`).join(",")
      )
      .join("\n");

    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    link.download = `facetrack-attendance-${selectedDate}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  const navItems = [
    ["overview", "Overview", "⌂"],
    ["employees", "Employees", "♙"],
    ["attendance", "Attendance", "◷"],
    ["offices", "Office kiosks", "▣"],
  ];

  // Office kiosk
  if (isOffice && page === "kiosk") {
    return (
      <main className="kiosk-page">
        <header className="kiosk-header">
          <Brand />
          <div><span className="live-dot" /> KIOSK ONLINE</div>
          <button className="button button-ghost" onClick={logout}>Exit</button>
        </header>

        <section className="kiosk-content">
          <div className="kiosk-heading">
            <span className="eyebrow">EMPLOYEE ATTENDANCE</span>
            <h1>Welcome to work.</h1>
            <p>Position your face inside the camera frame to mark attendance.</p>
          </div>

          <div className="kiosk-grid">
            <div className="camera-card">
              <div className="camera-frame">
                <video ref={videoRef} autoPlay muted playsInline />
                <div className="camera-guide" />
              </div>

              <button
                className="button button-primary button-wide"
                onClick={scanAttendance}
                disabled={loading}
              >
                {loading ? "Verifying face..." : "Scan & Mark Attendance"}
              </button>

              <p className="camera-note">Please look directly at the camera.</p>
            </div>

            <div className="scan-result-card">
              {scanResult ? (
                <div className="scan-success">
                  <div className="result-check">✓</div>
                  <span className="eyebrow">ATTENDANCE RECORDED</span>
                  <h2>{scanResult.employee?.name || "Employee"}</h2>
                  <p className="result-code">{scanResult.employee?.employee_code || ""}</p>
                  <div className="result-action">
                    {scanResult.attendance?.action === "check_in" ? "CHECK-IN" : "CHECK-OUT"}
                  </div>
                  <div className="result-details">
                    <div><span>Date</span><strong>{scanResult.attendance?.date || "—"}</strong></div>
                    <div><span>Time</span><strong>{formatISTTime(scanResult.attendance?.time)}</strong></div>
                    <div><span>Status</span><strong>{scanResult.attendance?.status || "—"}</strong></div>
                  </div>
                  <p className="result-message">{scanResult.message}</p>
                  <button className="button button-outline button-wide" onClick={() => setScanResult(null)}>
                    Next employee
                  </button>
                </div>
              ) : (
                <div className="scan-placeholder">
                  <div className="placeholder-icon">◎</div>
                  <h2>Ready to scan</h2>
                  <p>Employee details and attendance confirmation will appear here after a successful scan.</p>
                </div>
              )}
            </div>
          </div>

          {error && <div className="alert alert-error">{error}</div>}
          {message && <div className="alert alert-success">{message}</div>}
        </section>

        <footer className="kiosk-footer">
          {session.user?.name} · {session.user?.location || "Office kiosk"}
        </footer>
      </main>
    );
  }

  // Organization registration page
  if (!session && page === "register") {
    return (
      <main className="auth-page">
        <div className="auth-brand"><Brand /></div>

        <section className="auth-card registration-card">
          <span className="eyebrow">GET STARTED WITH FACETRACK</span>
          <h1>Create your workspace.</h1>
          <p className="muted">
            Register your organization and create its administrator account.
          </p>

          <form onSubmit={handleOrganizationRegister} className="form-stack">
            <h3>Organization details</h3>

            <label>
              Organization name
              <input
                value={organizationForm.name}
                onChange={(e) => setOrganizationForm({ ...organizationForm, name: e.target.value })}
                placeholder="Your company name"
                required
              />
            </label>

            <label>
              Organization email
              <input
                type="email"
                value={organizationForm.email}
                onChange={(e) => setOrganizationForm({ ...organizationForm, email: e.target.value })}
                placeholder="company@example.com"
                required
              />
            </label>

            <label>
              Phone number
              <input
                type="tel"
                value={organizationForm.phone}
                onChange={(e) => setOrganizationForm({ ...organizationForm, phone: e.target.value })}
                placeholder="Optional"
              />
            </label>

            <label>
              Organization address
              <textarea
                value={organizationForm.address}
                onChange={(e) => setOrganizationForm({ ...organizationForm, address: e.target.value })}
                placeholder="Company address (optional)"
                rows="3"
              />
            </label>

            <div className="registration-divider" />

            <h3>Administrator account</h3>

            <label>
              Admin full name
              <input
                value={organizationForm.admin_name}
                onChange={(e) => setOrganizationForm({ ...organizationForm, admin_name: e.target.value })}
                placeholder="Your full name"
                required
              />
            </label>

            <label>
              Admin email
              <input
                type="email"
                value={organizationForm.admin_email}
                onChange={(e) => setOrganizationForm({ ...organizationForm, admin_email: e.target.value })}
                placeholder="admin@example.com"
                required
              />
            </label>

            <label>
              Create password
              <input
                type="password"
                minLength="8"
                value={organizationForm.admin_password}
                onChange={(e) => setOrganizationForm({ ...organizationForm, admin_password: e.target.value })}
                placeholder="Minimum 8 characters"
                required
              />
            </label>

            {error && <div className="alert alert-error">{error}</div>}

            <button
              className="button button-primary button-wide"
              disabled={loading}
            >
              {loading ? "Creating organization..." : "Create organization"}
            </button>
          </form>

          <button
            className="back-home"
            onClick={() => {
              setPage("home");
              setError("");
            }}
          >
            ← Back to home
          </button>
        </section>
      </main>
    );
  }

  // Login page
  if (!session && page === "login") {
    return (
      <main className="auth-page">
        <div className="auth-brand"><Brand /></div>

        <section className="auth-card">
          <span className="eyebrow">SECURE ACCESS</span>
          <h1>Welcome back.</h1>
          <p className="muted">Sign in to continue to your FACETRACK workspace.</p>

          {message && <div className="alert alert-success">{message}</div>}

          {registeredOrganization && (
            <div className="alert alert-success">
              Your Organization ID: <strong>{registeredOrganization.organization_id}</strong>
            </div>
          )}

          <div className="auth-tabs">
            <button
              className={loginMode === "admin" ? "active" : ""}
              onClick={() => setLoginMode("admin")}
            >
              Admin login
            </button>
            <button
              className={loginMode === "office" ? "active" : ""}
              onClick={() => setLoginMode("office")}
            >
              Office kiosk
            </button>
          </div>

          <form onSubmit={handleLogin} className="form-stack">
            {loginMode === "admin" ? (
              <>
                <label>
                  Organization ID
                  <input
                    value={organizationId}
                    onChange={(e) => setOrganizationId(e.target.value)}
                    required
                  />
                </label>

                <label>
                  Email address
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </label>

                <label>
                  Password
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </label>
              </>
            ) : (
              <>
                <label>
                  Office ID
                  <input
                    value={officeId}
                    onChange={(e) => setOfficeId(e.target.value)}
                    required
                  />
                </label>

                <label>
                  Office PIN
                  <input
                    type="password"
                    inputMode="numeric"
                    value={pin}
                    onChange={(e) => setPin(e.target.value)}
                    required
                  />
                </label>
              </>
            )}

            {error && <div className="alert alert-error">{error}</div>}

            <button className="button button-primary button-wide" disabled={loading}>
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>

          <button
            className="back-home"
            onClick={() => {
              setPage("home");
              setError("");
              setMessage("");
            }}
          >
            ← Back to home
          </button>
        </section>
      </main>
    );
  }

  // Public home page
  if (!session) {
    return (
      <main className="home-page">
        <nav className="public-nav">
          <Brand />

          <div className="public-links">
            <a href="#features">Features</a>
            <a href="#how-it-works">How it works</a>
          </div>

          <div className="public-nav-actions">
            <button className="button button-outline" onClick={() => setPage("register")}>
              Create organization
            </button>
            <button className="button button-primary" onClick={() => setPage("login")}>
              Sign in <span>→</span>
            </button>
          </div>
        </nav>

        <section className="hero-section">
          <div className="hero-copy">
            <span className="eyebrow">
              <span className="live-dot" /> SMART WORKFORCE ATTENDANCE
            </span>

            <h1>Attendance that works as <span>smart as you do.</span></h1>

            <p>
              One intelligent workspace for employee attendance, face verification
              and multi-office workforce management.
            </p>

            <div className="hero-actions">
              <button
                className="button button-primary button-large"
                onClick={() => setPage("register")}
              >
                Create your organization <span>→</span>
              </button>

              <a className="text-link" href="#how-it-works">
                Explore how it works ↓
              </a>
            </div>

            <div className="hero-proof">
              <span>01 / FACE VERIFICATION</span>
              <span>02 / LIVE ATTENDANCE</span>
              <span>03 / MULTI-OFFICE</span>
            </div>
          </div>

          <div className="hero-visual">
            <div className="visual-glow" />

            <div className="preview-window">
              <div className="preview-topbar">
                <Brand />
                <span>WORKSPACE PREVIEW</span>
              </div>

              <div className="preview-body">
                <div className="preview-sidebar"><i /><i /><i /><i /></div>

                <div className="preview-main">
                  <span className="preview-label">TODAY'S OVERVIEW</span>
                  <h3>Good morning.</h3>

                  <div className="preview-stats">
                    <div><small>Employees</small><strong>248</strong><em>Workforce</em></div>
                    <div><small>Present today</small><strong>216</strong><em>Attendance</em></div>
                  </div>

                  <div className="preview-chart">
                    <div className="chart-head"><b>Attendance activity</b><small>THIS WEEK</small></div>
                    <div className="chart-bars">
                      {[38, 64, 48, 82, 58, 92, 70].map((h, i) => (
                        <i key={i} style={{ height: `${h}%` }} />
                      ))}
                    </div>
                    <div className="chart-days">
                      <span>M</span><span>T</span><span>W</span><span>T</span><span>F</span><span>S</span><span>S</span>
                    </div>
                  </div>

                  <div className="preview-notice">
                    <span>✓</span>
                    <div><b>Attendance verified</b><small>Employee check-in recorded</small></div>
                    <strong>09:02 AM</strong>
                  </div>
                </div>
              </div>
            </div>

            <div className="floating-chip chip-one"><span>✓</span> Face verified</div>
            <div className="floating-chip chip-two"><span className="live-dot" /> Live attendance</div>
          </div>
        </section>

        <section className="feature-strip" id="features">
          <div><span>01</span><b>Face-based attendance</b><p>Quick employee verification at the office kiosk.</p></div>
          <div><span>02</span><b>One unified dashboard</b><p>Manage employees and attendance in one place.</p></div>
          <div><span>03</span><b>Multiple office locations</b><p>Each office gets its own attendance kiosk.</p></div>
        </section>

        <section className="how-section" id="how-it-works">
          <span className="eyebrow">SIMPLE BY DESIGN</span>
          <h2>From face scan to attendance record.</h2>
          <p className="muted">A straightforward workflow for employees and administrators.</p>

          <div className="steps-grid">
            <div><span>01</span><h3>Set up your office</h3><p>Register an office and its dedicated kiosk.</p></div>
            <div><span>02</span><h3>Enroll employees</h3><p>Add employee details and enroll their face with consent.</p></div>
            <div><span>03</span><h3>Scan and manage</h3><p>Record attendance and review reports in your dashboard.</p></div>
          </div>
        </section>

        <section className="home-cta">
          <div>
            <span className="eyebrow">READY WHEN YOU ARE</span>
            <h2>Make attendance simpler.</h2>
            <p>Create your organization and get started with FACETRACK.</p>
          </div>

          <button className="button button-light" onClick={() => setPage("register")}>
            Create organization →
          </button>
        </section>

        <footer className="public-footer">
          <Brand />
          <span>© {new Date().getFullYear()} FACETRACK · Project by Neetesh Kumar and Garv Singhal</span>
        </footer>
      </main>
    );
  }

  // Admin dashboard
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Brand light />
        <div className="workspace-label">WORKSPACE</div>

        <nav className="side-nav">
          {navItems.map(([key, label, icon]) => (
            <button
              key={key}
              className={activePage === key ? "selected" : ""}
              onClick={() => {
                setActivePage(key);
                setHistory(null);
              }}
            >
              <span className="nav-icon">{icon}</span>{label}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="user-mini">
            <div className="avatar">{(session.user?.name || "A")[0]}</div>
            <div>
              <b>{session.user?.name || "Administrator"}</b>
              <small>Organization admin</small>
            </div>
          </div>

          <button className="logout-button" onClick={logout}>↪ Sign out</button>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div>
            <span className="eyebrow">ORGANIZATION WORKSPACE</span>
            <h2>{session.user?.organization_name || "FACETRACK"}</h2>
          </div>

          <div className="topbar-right">
            <span className="system-status"><i /> System connected</span>
            <div className="avatar avatar-top">{(session.user?.name || "A")[0]}</div>
          </div>
        </header>

        <div className="page-content">
          {error && (
            <div className="alert alert-error">
              {error}
              <button onClick={() => setError("")}>×</button>
            </div>
          )}

          {message && (
            <div className="alert alert-success">
              {message}
              <button onClick={() => setMessage("")}>×</button>
            </div>
          )}

          {history ? (
            <section className="content-section">
              <button className="back-home" onClick={() => setHistory(null)}>
                ← Back to employees
              </button>

              <div className="section-heading">
                <div>
                  <span className="eyebrow">EMPLOYEE RECORD</span>
                  <h1>{history.employee?.name || "Attendance history"}</h1>
                  <p>Historical attendance records</p>
                </div>
              </div>

              <div className="stats-grid">
                <Metric label="Total records" value={history.summary?.total_days ?? 0} />
                <Metric label="Present" value={history.summary?.present ?? 0} />
                <Metric label="Late" value={history.summary?.late ?? 0} />
              </div>

              <AttendanceTable records={history.history || []} />
            </section>
          ) : activePage === "overview" ? (
            <section className="content-section">
              <div className="section-heading">
                <div>
                  <span className="eyebrow">OVERVIEW</span>
                  <h1>Good to see you.</h1>
                  <p>Here's what's happening across your organization today.</p>
                </div>
                <div className="date-pill">{selectedDate}</div>
              </div>

              <div className="stats-grid">
                <Metric label="Total employees" value={summary.total_employees ?? employees.length} detail="Registered workforce" />
                <Metric label="Present today" value={summary.present ?? 0} detail="Attendance recorded" />
                <Metric label="Late arrivals" value={summary.late ?? 0} detail="Marked as late" />
                <Metric label="Office locations" value={offices.length} detail="Registered kiosks" />
              </div>

              <div className="dashboard-grid">
                <div className="panel attendance-panel">
                  <div className="panel-heading">
                    <div><h3>Today's attendance</h3><p>Real-time records from your organization</p></div>
                    <input type="date" value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)} />
                  </div>
                  <AttendanceTable records={attendance.slice(0, 6)} />
                </div>

                <div className="panel quick-panel">
                  <h3>Quick actions</h3>
                  <p>Manage your workforce</p>
                  <button onClick={() => { setActivePage("employees"); setShowEmployeeForm(true); }}>＋ Add employee</button>
                  <button onClick={() => setActivePage("offices")}>▣ Manage office kiosks</button>
                  <button onClick={() => setActivePage("attendance")}>◷ View attendance</button>
                </div>
              </div>
            </section>
          ) : activePage === "employees" ? (
            <section className="content-section">
              <div className="section-heading">
                <div>
                  <span className="eyebrow">PEOPLE MANAGEMENT</span>
                  <h1>Employees</h1>
                  <p>Manage employee profiles and face enrollment.</p>
                </div>
                <button className="button button-primary" onClick={() => setShowEmployeeForm(!showEmployeeForm)}>
                  ＋ Add employee
                </button>
              </div>

              {showEmployeeForm && (
                <form className="panel form-panel" onSubmit={addEmployee}>
                  <h3>Add new employee</h3>

                  <div className="form-grid">
                    {[
                      ["employee_code", "Employee ID *"],
                      ["name", "Full name *"],
                      ["email", "Email address"],
                      ["phone", "Phone number"],
                      ["department", "Department"],
                      ["designation", "Designation"],
                    ].map(([key, label]) => (
                      <label key={key}>
                        {label}
                        <input
                          required={label.includes("*")}
                          value={employeeForm[key]}
                          onChange={(e) => setEmployeeForm({ ...employeeForm, [key]: e.target.value })}
                        />
                      </label>
                    ))}

                    <label>
                      Joining date
                      <input
                        type="date"
                        value={employeeForm.joining_date}
                        onChange={(e) => setEmployeeForm({ ...employeeForm, joining_date: e.target.value })}
                      />
                    </label>

                    <label>
                      Profile photo
                      <input type="file" accept="image/*" onChange={(e) => setEmployeePhoto(e.target.files[0])} />
                    </label>
                  </div>

                  <div className="form-actions">
                    <button type="button" className="button button-outline" onClick={() => setShowEmployeeForm(false)}>Cancel</button>
                    <button className="button button-primary" disabled={loading}>
                      {loading ? "Saving..." : "Save employee"}
                    </button>
                  </div>
                </form>
              )}

              <div className="panel table-panel">
                <div className="panel-heading">
                  <div><h3>All employees</h3><p>{employees.length} registered employees</p></div>
                </div>

                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Employee</th><th>Employee ID</th><th>Department</th>
                        <th>Designation</th><th>Status</th><th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {employees.map((emp) => (
                        <tr key={emp.id}>
                          <td><b>{emp.name}</b><small>{emp.email || "—"}</small></td>
                          <td>{emp.employee_code}</td>
                          <td>{emp.department || "—"}</td>
                          <td>{emp.designation || "—"}</td>
                          <td><Status active={emp.is_active} /></td>
                          <td>
                            <div className="row-actions">
                              <button onClick={() => { setEnrollEmployee(emp); setEnrollImage(null); setConsent(false); }}>Enroll face</button>
                              <button onClick={() => openHistory(emp)}>History</button>
                            </div>
                          </td>
                        </tr>
                      ))}

                      {employees.length === 0 && (
                        <tr><td colSpan="6"><EmptyState text="No employees found. Add your first employee." /></td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {enrollEmployee && (
                <form className="panel form-panel" onSubmit={enrollFace}>
                  <h3>Face enrollment · {enrollEmployee.name}</h3>
                  <p className="muted">Select a clear face image. Employee consent is required.</p>

                  <label>
                    Face image
                    <input type="file" accept="image/*" onChange={(e) => setEnrollImage(e.target.files[0])} required />
                  </label>

                  <label className="checkbox-label">
                    <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
                    Employee has provided consent for face enrollment.
                  </label>

                  <div className="form-actions">
                    <button type="button" className="button button-outline" onClick={() => setEnrollEmployee(null)}>Cancel</button>
                    <button className="button button-primary" disabled={loading}>Enroll face</button>
                  </div>
                </form>
              )}
            </section>
          ) : activePage === "attendance" ? (
            <section className="content-section">
              <div className="section-heading">
                <div>
                  <span className="eyebrow">ATTENDANCE MANAGEMENT</span>
                  <h1>Attendance records</h1>
                  <p>Review check-ins, check-outs and daily status.</p>
                </div>

                <div className="heading-actions">
                  <input type="date" value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)} />
                  <button className="button button-outline" onClick={exportCSV}>↓ Export CSV</button>
                </div>
              </div>

              <div className="stats-grid">
                <Metric label="Total employees" value={summary.total_employees ?? 0} />
                <Metric label="Present" value={summary.present ?? 0} />
                <Metric label="Late" value={summary.late ?? 0} />
                <Metric label="Absent" value={summary.absent ?? 0} />
              </div>

              <div className="panel table-panel">
                <div className="panel-heading">
                  <div><h3>Daily attendance</h3><p>{selectedDate}</p></div>
                </div>
                <AttendanceTable records={attendance} />
              </div>
            </section>
          ) : (
            <section className="content-section">
              <div className="section-heading">
                <div>
                  <span className="eyebrow">LOCATION MANAGEMENT</span>
                  <h1>Office kiosks</h1>
                  <p>One dedicated attendance screen for each physical office.</p>
                </div>
              </div>

              <form className="panel form-panel" onSubmit={addOffice}>
                <h3>Register an office kiosk</h3>

                <div className="form-grid">
                  <label>
                    Office name
                    <input required value={officeForm.device_name} onChange={(e) => setOfficeForm({ ...officeForm, device_name: e.target.value })} placeholder="e.g. Delhi Head Office" />
                  </label>

                  <label>
                    Location
                    <input required value={officeForm.location} onChange={(e) => setOfficeForm({ ...officeForm, location: e.target.value })} placeholder="Office address / city" />
                  </label>

                  <label>
                    Office PIN
                    <input required minLength="4" maxLength="12" inputMode="numeric" value={officeForm.pin} onChange={(e) => setOfficeForm({ ...officeForm, pin: e.target.value })} placeholder="4–12 digit PIN" />
                  </label>
                </div>

                <div className="form-actions">
                  <button className="button button-primary" disabled={loading}>Register kiosk</button>
                </div>
              </form>

              <div className="office-grid">
                {offices.map((office) => (
                  <div className="panel office-card" key={office.id}>
                    <div className="office-icon">▣</div>
                    <Status active={office.is_active} />
                    <h3>{office.name}</h3>
                    <p>{office.location || "Location not specified"}</p>
                    <small>Office ID: {office.id}</small>
                    {office.is_active && (
                      <button className="danger-link" onClick={() => deactivateOffice(office.id)}>
                        Deactivate kiosk
                      </button>
                    )}
                  </div>
                ))}

                {offices.length === 0 && (
                  <div className="panel"><EmptyState text="No office kiosks registered yet." /></div>
                )}
              </div>
            </section>
          )}
        </div>
      </main>
    </div>
  );
}

function Metric({ label, value, detail }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail || " "}</small>
    </div>
  );
}

function Status({ active }) {
  return (
    <span className={`status-pill ${active ? "status-active" : "status-inactive"}`}>
      <i />{active ? "Active" : "Inactive"}
    </span>
  );
}

function EmptyState({ text }) {
  return <div className="empty-state"><span>⌕</span><p>{text}</p></div>;
}

function AttendanceTable({ records }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Employee</th><th>Date</th><th>Check in</th>
            <th>Check out</th><th>Working time</th><th>Status</th>
          </tr>
        </thead>
        <tbody>
          {records.map((r, i) => (
            <tr key={r.attendance_id || `${r.employee_id}-${r.date}-${i}`}>
              <td><b>{r.employee_name || "—"}</b><small>{r.employee_code || ""}</small></td>
              <td>{r.date || "—"}</td>
              <td>{formatISTTime(r.check_in)}</td>
              <td>{formatISTTime(r.check_out)}</td>
              <td>
                {r.total_working_minutes != null
                  ? `${Math.floor(r.total_working_minutes / 60)}h ${r.total_working_minutes % 60}m`
                  : `${r.working_minutes ?? 0} min`}
              </td>
              <td>
                <span className={`status-pill ${r.status === "Late" ? "status-late" : "status-active"}`}>
                  <i />{r.status || "—"}
                </span>
              </td>
            </tr>
          ))}

          {records.length === 0 && (
            <tr><td colSpan="6"><EmptyState text="No attendance records for this date." /></td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export default App;
