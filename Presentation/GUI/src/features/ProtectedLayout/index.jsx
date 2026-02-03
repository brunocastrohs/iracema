import { Outlet, Navigate } from "react-router-dom";
import { useState } from "react";
import Navigator from "../Navigator";
import "./styles.css";

function hasValidToken() {
  const token =
    localStorage.getItem("iracema_token") ||
    sessionStorage.getItem("iracema_token");
  return Boolean(token);
}

export default function ProtectedLayout() {
  const [navCollapsed, setNavCollapsed] = useState(false);

  if (!hasValidToken()) return <Navigate to="/" replace />;

  return (
    <div className={`protected-layout ${navCollapsed ? "nav-collapsed" : ""}`}>
      <Navigator collapsed={navCollapsed} onToggleCollapsed={setNavCollapsed} />

      <main className="protected-content">
        <Outlet />
      </main>
    </div>
  );
}
