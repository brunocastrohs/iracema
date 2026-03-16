import { NavLink } from "react-router-dom";
import "./styles.css";
import logo from "../../_assets/images/logo_iracema.png";

export default function Navigator({ collapsed, onToggleCollapsed }) {
  return (
    <div className="sidebar-wrapper">
      <button
        className="toggle-button"
        onClick={() => onToggleCollapsed(!collapsed)}
        title={collapsed ? "Abrir menu" : "Fechar menu"}
      >
        ☰
      </button>

      {!collapsed && (
        <aside className="sidebar">
          <div
            className="logo-container"
            style={{ backgroundImage: `url(${logo})` }}
          />

          <nav>
            <ul>
              <li>
                <NavLink
                  to="/chat"
                  className={({ isActive }) => (isActive ? "active" : "")}
                >
                  <i className="pi pi-comments" /> Chat
                </NavLink>
              </li>

              <li>
                <NavLink
                  to="/config"
                  className={({ isActive }) => (isActive ? "active" : "")}
                >
                  <i className="pi pi-cog" /> Configuração
                </NavLink>
              </li>
            </ul>
          </nav>
        </aside>
      )}
    </div>
  );
}