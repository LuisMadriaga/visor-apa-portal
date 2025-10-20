import React, { useEffect, useState } from "react";
import VisorReportes from "./components/VisorReportes";

function App() {
  const [informes, setInformes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rutPaciente, setRutPaciente] = useState(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const rut = params.get("rut");
    setRutPaciente(rut);
    if (!rut) {
      setLoading(false);
      return;
    }

    // ✅ CORRECCIÓN: Detectar correctamente el entorno
    const host = window.location.hostname;
    const port = window.location.port;
    let API_BASE;

    // Si estamos en desarrollo local (npm start)
    if (host === "localhost" && port === "3000") {
      API_BASE = "http://localhost:8000";
    } 
    // Si estamos en producción/Docker (accediendo por :8080 o sin puerto)
    else {
      API_BASE = "/api";  // ✅ Usar ruta relativa para que nginx maneje el proxy
    }

    console.log("🌐 API_BASE =", API_BASE);
    console.log("📡 Fetching:", `${API_BASE}/informes-list/${rut}/`);

    fetch(`${API_BASE}/informes-list/${rut}/`)
      .then((res) => {
        console.log("📄 Response status:", res.status);
        return res.json();
      })
      .then((data) => {
        console.log("✅ Data recibida:", data);
        setInformes(data);
      })
      .catch((err) => {
        console.error("❌ Error en fetch:", err);
        setInformes([]);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading)
    return (
      <p style={{ textAlign: "center", marginTop: "3rem" }}>Cargando...</p>
    );

  if (!rutPaciente)
    return (
      <p style={{ textAlign: "center", marginTop: "3rem" }}>
        ⚠️ Falta el parámetro <strong>rut</strong> en la URL.
      </p>
    );

  if (!informes.length)
    return (
      <p style={{ textAlign: "center", marginTop: "3rem" }}>
        No se encontraron informes para el RUT {rutPaciente}.
      </p>
    );

  return <VisorReportes informes={informes} />;
}

export default App;