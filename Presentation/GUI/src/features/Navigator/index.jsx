import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import "./styles.css";
import logo from "../../_assets/images/logo_iracema.png";

export default function Navigator() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.clear();
    sessionStorage.clear();
    navigate("/", { replace: true });
  };

  return (
    <div className={`sidebar-wrapper ${collapsed ? "collapsed" : ""}`}>
      <button
        className="toggle-button"
        onClick={() => setCollapsed(!collapsed)}
        title={collapsed ? "Abrir menu" : "Fechar menu"}
      >
        ☰
      </button>

      <aside className="sidebar">
        <div className="logo-container" style={{ backgroundImage: `url(${logo})` }} />

        <nav>
          <ul>
            <li>
              <NavLink to="/layers" className={({ isActive }) => (isActive ? "active" : "")}>
                <i className="pi pi-map-marker" /> Camadas
              </NavLink>
            </li>
            <li>
              <NavLink to="/upload" className={({ isActive }) => (isActive ? "active" : "")}>
                <i className="pi pi-map-marker" /> Importar
              </NavLink>
            </li>
            {/*<li>
              <NavLink to="/history" className={({ isActive }) => (isActive ? "active" : "")}>
                <i className="pi pi-clock" /> Histórico
              </NavLink>
            </li>*/}
          </ul>
        </nav>

        <div style={{ marginTop: "auto", padding: "10px 20px" }}>
          <button className="nav__logout" onClick={handleLogout}>
            Sair
          </button>
        </div>
      </aside>
    </div>
  );
}
