import { BrowserRouter, Routes, Route } from "react-router-dom";
import Auth from "./features/Auth/index";
import Layers from "./features/Layers";
import Uploader from "./features/Uploader";
import "./_assets/styles/global.css";

import ProtectedLayout from "./features/ProtectedLayout";

function History() {
  return <h1 className="section-title">Histórico</h1>;
}


export default function App() {
  return (
    <BrowserRouter basename="/iracema">
      <Routes>
        <Route path="/" element={<Auth />} />

        <Route element={<ProtectedLayout />}>
          <Route path="/layers" element={<Layers />} />
          <Route path="/upload" element={<Uploader />} />
          <Route path="/history" element={<History />} />
        </Route>

      </Routes>
    </BrowserRouter>
  );
}
