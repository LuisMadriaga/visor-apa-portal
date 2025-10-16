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

    const API_BASE = window.location.hostname.includes("localhost")
      ? "http://localhost:8000"
      : "http://172.16.8.194:8000";

    fetch(`${API_BASE}/api/informes-list/${rut}/`)
      .then((res) => res.json())
      .then((data) => setInformes(data))
      .catch(() => setInformes([]))
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