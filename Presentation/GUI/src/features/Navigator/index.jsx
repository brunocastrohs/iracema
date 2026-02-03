import { NavLink, useNavigate } from "react-router-dom";
import "./styles.css";
import logo from "../../_assets/images/logo_iracema.png";

export default function Navigator({ collapsed, onToggleCollapsed }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.clear();
    sessionStorage.clear();
    navigate("/", { replace: true });
  };

  return (
    <div className="sidebar-wrapper">
      <button
        className="toggle-button"
        onClick={() => onToggleCollapsed(!collapsed)}
        title={collapsed ? "Abrir menu" : "Fechar menu"}
      >
        ☰
      </button>

      {/* Quando colapsado, a coluna fica 0, então nem precisa renderizar animação */}
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

          <div style={{ marginTop: "auto", padding: "10px 20px" }}>
            <button className="nav__logout" onClick={handleLogout}>
               <i className="pi pi-sign-out" /> Sair
            </button>
          </div>
        </aside>
      )}
    </div>
  );
}
