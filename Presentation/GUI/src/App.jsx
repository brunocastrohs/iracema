import { BrowserRouter, Routes, Route } from "react-router-dom";
import Auth from "./features/Auth/index";
import Chat from "./features/Chat";
import Configuration from "./features/Configuration";
import "./_assets/styles/global.css";
import "primeicons/primeicons.css";


import ProtectedLayout from "./features/ProtectedLayout";

export default function App() {
  return (
    <BrowserRouter basename="/iracema">
      <Routes>
        <Route path="/" element={<Auth />} />

        <Route element={<ProtectedLayout />}>
          <Route path="/chat" element={<Chat />} />
          <Route path="/config" element={<Configuration />} />
        </Route>

      </Routes>
    </BrowserRouter>
  );
}
