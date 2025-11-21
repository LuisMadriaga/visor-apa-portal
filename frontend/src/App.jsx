// App.jsx
import React, { useEffect, useState } from "react";
import VisorReportes from "./components/VisorReportes";
import MensajeResultados from "./components/MensajeResultados";

function App() {
  const [informes, setInformes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [rutPaciente, setRutPaciente] = useState(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");

    if (!token) {
      setError("⚠️ Falta el parámetro token en la URL");
      setLoading(false);
      return;
    }

    const host = window.location.hostname;
    const port = window.location.port;
    let API_BASE;

    if (host === "localhost" && port === "3000") {
      API_BASE = "http://localhost:8000";
    } else {
      API_BASE = "/visor_apa_portal_2/api";
    }


    // 🔹 Validar token y obtener informes
    fetch(`${API_BASE}/validate-access/?token=${encodeURIComponent(token)}`)
      .then((res) => {
        if (!res.ok) {
          throw new Error("Token inválido o expirado");
        }
        return res.json();
      })
      .then((data) => {
        if (!data.valid) {
          throw new Error(data.error || "Token no válido");
        }

        const rut = data.rut;
        setRutPaciente(rut);

        return fetch(`${API_BASE}/informes-list/${rut}/`);
      })
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Error ${res.status}: ${res.statusText}`);
        }
        return res.json();
      })
      .then((data) => {
        setInformes(data);
      })
      .catch((err) => {
        console.error("❌ Error:", err);
        setError(err.message);
        setInformes([]);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", background: "#f1f5f9" }}>
        <p style={{ fontSize: "1.2rem", color: "#00558a" }}>⏳ Cargando...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", height: "100vh", background: "#f1f5f9" }}>
        <h3 style={{ color: "#d32f2f", marginBottom: "1rem" }}>❌ Error</h3>
        <p style={{ fontSize: "1.1rem", color: "#555" }}>{error}</p>
      </div>
    );
  }

  if (!informes || informes.length === 0) {
    return <MensajeResultados />;
  }

  return <VisorReportes informes={informes} />;
}

export default App;