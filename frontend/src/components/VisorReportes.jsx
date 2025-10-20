import { useEffect, useState, useRef } from "react";
import * as pdfjsLib from "pdfjs-dist";

// Usar worker local desde la carpeta public
pdfjsLib.GlobalWorkerOptions.workerSrc = `${window.location.origin}/pdf.worker.min.mjs`;

// Alternativa: Para desarrollo local con Vite
// pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
//   "pdfjs-dist/build/pdf.worker.min.mjs",
//   import.meta.url
// ).toString();

export default function VisorReportes() {
  const [informes, setInformes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const canvasRef = useRef(null);

  // Detectar tamaño de pantalla
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (mobile) setSidebarOpen(false);
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const rut = params.get("rut");  // ✅ toma el rut desde la URL

    const host = window.location.hostname;
    const port = window.location.port;
    let API_BASE;

    // ✅ Configuración correcta para Docker y desarrollo local
    if (host === "localhost" && port === "3000") {
      API_BASE = "http://localhost:8000";  // solo para desarrollo
    } else {
      API_BASE = "/api";  // ✅ Nginx hace el proxy
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

        // 🔧 Corregir URLs de PDFs para incluir el puerto correcto (solo si aplica)
        const correctedData = data.map(item => {
          if (item.url && !item.url.includes(':8080')) {
            item.url = item.url.replace(
              'http://172.16.8.194/',
              'http://172.16.8.194:8080/'
            );
          }
          return item;
        });

        const sorted = [...correctedData].sort(
          (a, b) => b.numero_biopsia - a.numero_biopsia
        );
        setInformes(sorted);
      })
      .catch((err) => {
        console.error("❌ Error al obtener informes:", err);
      })
      .finally(() => setLoading(false));
  }, []); // ✅ sin 'rut' en dependencias

  // 🖼️ Renderizar miniatura (primera página)
  useEffect(() => {
    if (!informes.length) return;

    const pdfUrl = informes[selectedIndex].url;
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    canvas.width = 0;
    canvas.height = 0;

    // 🧩 Cargar PDF y mantener referencia al worker
    const loadingTask = pdfjsLib.getDocument(pdfUrl);
    let pageInstance = null;

    loadingTask.promise
      .then((pdf) => pdf.getPage(1))
      .then((page) => {
        pageInstance = page;
        // Escala adaptativa según el tamaño de pantalla
        const scale = isMobile ? 1.5 : 1.2;
        const viewport = page.getViewport({ scale });
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        const renderContext = { canvasContext: ctx, viewport };
        page.render(renderContext);
      })
      .catch((err) => {
        // 🚫 Ignorar "Worker was destroyed", mostrar los demás
        if (err && err.message !== "Worker was destroyed") {
          console.error("Error al generar miniatura PDF:", err);
        }
      });

    // 🧹 Limpieza
    return () => {
      try {
        loadingTask.destroy(); // ✅ Cierra el worker
        if (pageInstance) pageInstance.cleanup(); // limpia memoria
      } catch (e) {
        if (!/Worker was destroyed/.test(e.message)) {
          console.warn("Error al cerrar worker:", e.message);
        }
      }
    };
  }, [informes, selectedIndex, isMobile]);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", background: "#f1f5f9" }}>
        <p style={{ fontSize: "1.2rem", color: "#00558a" }}>⏳ Cargando informes...</p>
      </div>
    );
  }

  if (!informes.length) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", background: "#f1f5f9" }}>
        <p style={{ fontSize: "1.2rem", color: "#555" }}>⚠️ No hay informes disponibles.</p>
      </div>
    );
  }

  const selectedInforme = informes[selectedIndex];

  return (
    <div style={{ display: "flex", height: "100vh", background: "#f1f5f9", overflow: "hidden" }}>
      {/* Botón toggle móvil */}
      {isMobile && (
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          style={{
            position: "fixed",
            top: "1rem",
            left: sidebarOpen ? "280px" : "1rem",
            zIndex: 1000,
            background: "#003366",
            color: "#fff",
            border: "none",
            borderRadius: "50%",
            width: "48px",
            height: "48px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
            transition: "left 0.3s ease",
            fontSize: "1.5rem",
            fontWeight: "bold",
          }}
        >
          {sidebarOpen ? "‹" : "›"}
        </button>
      )}

      {/* Sidebar */}
      <div
        style={{
          width: sidebarOpen ? "300px" : "0",
          background: "#fff",
          boxShadow: "2px 0 8px rgba(0,0,0,0.1)",
          overflowY: "auto",
          transition: "width 0.3s ease",
          flexShrink: 0,
          position: isMobile ? "fixed" : "relative",
          height: "100vh",
          zIndex: 999,
        }}
      >
        {sidebarOpen && (
          <div style={{ padding: "1rem" }}>
            <h3 style={{ margin: "0 0 1rem 0", color: "#003366", fontSize: "1.1rem", borderBottom: "2px solid #003366", paddingBottom: "0.5rem" }}>
              Informes ({informes.length})
            </h3>
            {informes.map((inf, index) => (
              <div
                key={`${inf.numero_biopsia}-${index}`}
                onClick={() => {
                  setSelectedIndex(index);
                  if (isMobile) setSidebarOpen(false);
                }}
                style={{
                  padding: "0.75rem",
                  marginBottom: "0.5rem",
                  background: selectedIndex === index ? "#e3f2fd" : "#f8f9fa",
                  border: selectedIndex === index ? "2px solid #003366" : "1px solid #e0e0e0",
                  borderRadius: "8px",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
              >
                <div style={{ fontWeight: "600", color: "#003366", fontSize: "0.95rem" }}>
                  Biopsia N° {inf.numero_biopsia}
                </div>
                <div style={{ fontSize: "0.8rem", color: "#666" }}>
                  {inf.nombre}
                </div>
                <div style={{ fontSize: "0.75rem", color: "#888" }}>
                  {inf.fecha}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Área principal */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Encabezado */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
            padding: "0.8rem 1rem",
            background: "#0b2b5b",
            color: "#fff",
            width: "100%",
            flexShrink: 0,
            boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
          }}
        >
          {/* Logo FALP alineado a la izquierda */}
          <img
            src={`http://172.16.8.194:8080/static/img/logo_falp4.png?v=${Date.now()}`}
            alt="Logo FALP"
            style={{
              position: "absolute",
              left: "20px",
              height: "42px",
              objectFit: "contain",
            }}
          />

          {/* Texto centrado */}
          <div style={{ textAlign: "center" }}>
            <h3 style={{ margin: 0, fontWeight: "bold" }}>
              Biopsia N° {selectedInforme.numero_biopsia} ({selectedIndex + 1} de {informes.length})
            </h3>
            <p style={{ margin: 0, fontSize: "0.9rem", opacity: 0.9 }}>
              Paciente: {selectedInforme.nombre} • {selectedInforme.rut}
            </p>
          </div>
        </div>

        {/* Miniatura + botón */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            background: "#f7f9fb",
            overflowY: "auto",
            padding: isMobile ? "1rem" : "2rem",
          }}
        >
          <canvas
            ref={canvasRef}
            style={{
              border: "1px solid #ccc",
              borderRadius: "10px",
              boxShadow: "0 3px 10px rgba(0,0,0,0.1)",
              maxWidth: "100%",
              width: isMobile ? "100%" : "auto",
              height: "auto",
              marginBottom: "1.5rem",
              background: "#fff",
            }}
          />
          <button
            onClick={() => window.open(selectedInforme.url, "_blank")}
            style={{
              background: "#003366",
              color: "#fff",
              border: "none",
              borderRadius: "8px",
              padding: isMobile ? "0.7rem 1.5rem" : "0.8rem 2rem",
              fontSize: isMobile ? "0.9rem" : "1rem",
              cursor: "pointer",
              boxShadow: "0 3px 8px rgba(0,0,0,0.2)",
              transition: "background 0.3s ease",
            }}
            onMouseOver={(e) => (e.currentTarget.style.background = "#004c99")}
            onMouseOut={(e) => (e.currentTarget.style.background = "#003366")}
          >
            🔍 Ver informe completo
          </button>
        </div>
      </div>
    </div>
  );
}