import { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";

pdfjsLib.GlobalWorkerOptions.workerSrc = `${window.location.origin}/pdf.worker.min.mjs`;

// para pruebas locales fuera de docker (reemplaza lo anterior)
// pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
//   "pdfjs-dist/build/pdf.worker.min.mjs",
//   import.meta.url
// ).toString();

// Componente PdfVisor mejorado
function PdfVisor({ pdfUrl }) {
  const pdfWrapperRef = useRef(null);
  const externalNodeRef = useRef(null);
  const [isLoading, setIsLoading] = useState(true);
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const updateScale = () => {
      if (window.innerWidth < 600) setScale(0.8);
      else if (window.innerWidth < 1024) setScale(0.9);
      else setScale(1.1);
    };
    updateScale();
    window.addEventListener("resize", updateScale);
    return () => window.removeEventListener("resize", updateScale);
  }, []);

  useEffect(() => {
    const wrapper = pdfWrapperRef.current;
    const externalDiv = document.createElement("div");
    externalDiv.style.width = "100%";
    externalDiv.style.maxWidth = "900px";
    externalDiv.style.background = "#fff";
    externalDiv.style.borderRadius = "12px";
    externalDiv.style.padding = "1rem";
    externalDiv.style.margin = "0 auto";

    wrapper.appendChild(externalDiv);
    externalNodeRef.current = externalDiv;

    return () => {
      wrapper.removeChild(externalDiv);
      externalNodeRef.current = null;
    };
  }, []);

  useEffect(() => {
    const container = externalNodeRef.current;
    if (!container) return;

    container.replaceChildren();
    setIsLoading(true);
    let cancelado = false;
    let pdfInstance = null;

    // 🧩 Crear la tarea de carga del PDF
    const loadingTask = pdfjsLib.getDocument(pdfUrl);

    loadingTask.promise
      .then((pdf) => {
        if (cancelado) return;
        pdfInstance = pdf;
        setIsLoading(false);

        const flex = document.createElement("div");
        flex.style.display = "flex";
        flex.style.flexDirection = "column";
        flex.style.alignItems = "center";
        flex.style.gap = "1.5rem";
        container.appendChild(flex);

        for (let i = 1; i <= pdf.numPages; i++) {
          pdf.getPage(i).then((page) => {
            if (cancelado) return;
            const viewport = page.getViewport({ scale });
            const canvas = document.createElement("canvas");
            const ctx = canvas.getContext("2d");
            canvas.height = viewport.height;
            canvas.width = viewport.width;
            canvas.style.maxWidth = "100%";
            canvas.style.borderRadius = "8px";
            canvas.style.boxShadow = "0 2px 10px rgba(0,0,0,0.15)";
            flex.appendChild(canvas);
            page.render({ canvasContext: ctx, viewport });
          });
        }
      })
      .catch((err) => {
        // 🚫 Ignorar el error "Worker was destroyed", mostrar otros
        if (err && err.message !== "Worker was destroyed") {
          console.error("Error al cargar PDF:", err);
          container.innerHTML =
            "<p style='color:red; text-align:center;'>⚠️ No se pudo cargar el PDF</p>";
        }
      });

    // 🧹 Limpieza al desmontar el componente
    return () => {
      cancelado = true;
      try {
        loadingTask.destroy(); // ✅ Cierra correctamente el worker
        if (pdfInstance) pdfInstance.destroy();
      } catch (e) {
        console.warn("Worker finalizado:", e.message);
      }
      container.replaceChildren();
    };
  }, [pdfUrl, scale]);

  return (
    <div
      ref={pdfWrapperRef}
      style={{
        background: "#f5f8fa",
        padding: "1rem",
        display: "flex",
        justifyContent: "center",
        alignItems: "flex-start",
        minHeight: "100%",
      }}
    >
      {isLoading && (
        <p style={{ textAlign: "center", color: "#00558a", width: "100%" }}>
          ⏳ Cargando documento...
        </p>
      )}
    </div>
  );
}

// Componente principal mejorado
export default function VisorReportes() {
  const [informes, setInformes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      setSidebarOpen(!mobile);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);


    useEffect(() => {
      const params = new URLSearchParams(window.location.search);
      const rut = params.get("rut");

      const host = window.location.hostname;
      const port = window.location.port;
      let API_BASE;

      // ✅ En desarrollo local (React en localhost:3000)
      if (host === "localhost" && port === "3000") {
        API_BASE = "http://localhost:8080";
      } 
      // ✅ En cualquier otro caso (Docker con Nginx)
      else {
        API_BASE = "/api";  // Nginx redirige a backend
      }

      console.log("🌍 API_BASE =", API_BASE);
      console.log("📡 Fetching:", `${API_BASE}/informes-list/${rut}/`);

      fetch(`${API_BASE}/informes-list/${rut}/`)
        .then(res => res.json())
        .then(data => {
          console.log("✅ Data recibida:", data);
        })
        .catch(err => console.error("❌ Error:", err));
    }, []);




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
      {/* Botón toggle para móvil */}
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
            width: "40px",
            height: "40px",
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

      {/* Sidebar con miniaturas */}
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
          left: 0,
          top: 0,
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
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                }}
                onMouseEnter={(e) => {
                  if (selectedIndex !== index) {
                    e.currentTarget.style.background = "#e8f4f8";
                    e.currentTarget.style.borderColor = "#90caf9";
                  }
                }}
                onMouseLeave={(e) => {
                  if (selectedIndex !== index) {
                    e.currentTarget.style.background = "#f8f9fa";
                    e.currentTarget.style.borderColor = "#e0e0e0";
                  }
                }}
              >
                <div
                  style={{
                    width: "32px",
                    height: "32px",
                    background: selectedIndex === index ? "#003366" : "#ddd",
                    borderRadius: "6px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  <span style={{ color: "#fff", fontSize: "1.2rem" }}>📄</span>
                </div>
                <div style={{ flex: 1, textAlign: "left" }}>
                  <div style={{ fontWeight: "600", color: "#003366", fontSize: "0.95rem" }}>
                    Biopsia N° {inf.numero_biopsia}
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "#666", marginTop: "0.25rem" }}>
                    {inf.nombre}
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "#888", marginTop: "0.1rem" }}>
                    RUT: {inf.rut}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Área principal del visor */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Visor de PDF con scroll */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            overflowX: "hidden",
            background: "#f7f9fb",
            WebkitOverflowScrolling: "touch",
          }}
        >
          <PdfVisor key={selectedInforme.numero_biopsia} pdfUrl={selectedInforme.url} />
        </div>
      </div>
    </div>
  );
}