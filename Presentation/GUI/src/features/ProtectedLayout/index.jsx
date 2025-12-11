import { Outlet, Navigate } from "react-router-dom";
import Navigator from "../Navigator";

import "./styles.css";


function hasValidToken() {
  const token =
    localStorage.getItem("iracema_token") ||
    sessionStorage.getItem("iracema_token");
  return Boolean(token);
}

export default function ProtectedLayout() {
  if (!hasValidToken()) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="protected-layout">
      <Navigator />
      <main className="protected-content">
        <Outlet />
      </main>
    </div>
  );
}
