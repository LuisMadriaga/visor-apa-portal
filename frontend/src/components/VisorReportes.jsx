// VisorReportes.jsx (CORREGIDO FINAL)
import { useEffect, useState, useRef } from "react";
import * as pdfjsLib from "pdfjs-dist";

pdfjsLib.GlobalWorkerOptions.workerSrc = `${window.location.origin}/pdf.worker.min.mjs`;

export default function VisorReportes({ informes }) {
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
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // Renderizar miniatura PDF
  useEffect(() => {
    if (!informes || informes.length === 0) return;

    const pdfUrl = informes[selectedIndex].url;
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    canvas.width = 0;
    canvas.height = 0;

    const loadingTask = pdfjsLib.getDocument(pdfUrl);
    let pageInstance = null;

    loadingTask.promise
      .then((pdf) => pdf.getPage(1))
      .then((page) => {
        pageInstance = page;
        const scale = isMobile ? 1.5 : 1.2;
        const viewport = page.getViewport({ scale });
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        const renderContext = { canvasContext: ctx, viewport };
        page.render(renderContext);
      })
      .catch((err) => {
        if (err && err.message !== "Worker was destroyed") {
          console.error("Error al generar miniatura PDF:", err);
        }
      });

    return () => {
      try {
        loadingTask.destroy();
        if (pageInstance) pageInstance.cleanup();
      } catch (e) {
        if (!/Worker was destroyed/.test(e.message)) {
          console.warn("Error al cerrar worker:", e.message);
        }
      }
    };
  }, [informes, selectedIndex, isMobile]);

  // Validación temprana
  if (!informes || informes.length === 0) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
          background: "#f1f5f9",
        }}
      >
        <p style={{ fontSize: "1.2rem", color: "#555" }}>
          ⚠️ No hay informes disponibles.
        </p>
      </div>
    );
  }

  const selectedInforme = informes[selectedIndex];

  return (
    <div
      style={{
        display: "flex",
        height: "100vh",
        background: "#f1f5f9",
        overflow: "hidden",
      }}
    >
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
            border: "2px solid #FFD700",        // 🟡 borde amarillo
            borderRadius: "50%",
            width: "48px",
            height: "48px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            boxShadow: "0 0 10px rgba(255, 215, 0, 0.5)", // ✨ brillo opcional
            transition: "left 0.3s ease, box-shadow 0.3s ease",
            fontSize: "1.5rem",
            fontWeight: "bold",
          }}
          onMouseOver={(e) =>
            (e.currentTarget.style.boxShadow = "0 0 15px rgba(255, 215, 0, 0.8)")
          }
          onMouseOut={(e) =>
            (e.currentTarget.style.boxShadow = "0 0 10px rgba(255, 215, 0, 0.5)")
          }
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
            <h3
              style={{
                margin: "0 0 1rem 0",
                color: "#003366",
                fontSize: "1.1rem",
                borderBottom: "2px solid #003366",
                paddingBottom: "0.5rem",
              }}
            >
              Informes ({informes.length})
            </h3>
            {informes.length > 0 && (
              <p
                style={{
                  fontSize: "14px",
                  fontWeight: "500",
                  marginTop: "4px",
                  color: "#333",
                }}
              >
                Paciente: {informes[0].nombre} • {informes[0].rut}
              </p>
            )}
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
                  background:
                    selectedIndex === index ? "#e3f2fd" : "#f8f9fa",
                  border:
                    selectedIndex === index
                      ? "2px solid #003366"
                      : "1px solid #e0e0e0",
                  borderRadius: "8px",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
              >
                <div
                  style={{
                    fontWeight: "600",
                    color: "#003366",
                    fontSize: "0.95rem",
                  }}
                >
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
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Encabezado responsivo */}
        <div
          style={{
            display: "flex",
            flexDirection: isMobile ? "column" : "row",
            alignItems: "center",
            justifyContent: isMobile ? "center" : "space-between",
            padding: "0.8rem 1rem",
            background: "#0b2b5b",
            color: "#fff",
            width: "100%",
            flexShrink: 0,
            boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
            textAlign: isMobile ? "center" : "left",
            gap: isMobile ? "0.4rem" : "1rem",
          }}
        >
          {/* Logo */}
          <img
            src={`/static/img/logo_falp4.png?v=${Date.now()}`}
            alt="Logo FALP"
            style={{
              height: isMobile ? "34px" : "42px",
              objectFit: "contain",
              marginBottom: isMobile ? "0.3rem" : "0",
            }}
          />

          {/* Texto central */}
          <div
            style={{
              flex: isMobile ? "0 0 auto" : "1 1 auto",
              textAlign: isMobile ? "center" : "left", // 🔹 cambia "right" por "left"
              lineHeight: 1.2,
              paddingLeft: isMobile ? "0.0rem" : "1rem", // 🔹 mueve un poco a la izquierda
              paddingRight: isMobile ? "0.5rem" : "0.8rem", // 🔹 deja un respiro visual
            }}
          >

            <h3
              style={{
                margin: 0,
                fontWeight: "bold",
                fontSize: isMobile ? "0.95rem" : "1rem",
              }}
            >
              Biopsia N° {selectedInforme.numero_biopsia} ({selectedIndex + 1}{" "}
              de {informes.length})
            </h3>
            <p
              style={{
                margin: 0,
                fontSize: "0.9rem",
                opacity: 0.9,
              }}
            >
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
            onMouseOver={(e) =>
              (e.currentTarget.style.background = "#004c99")
            }
            onMouseOut={(e) =>
              (e.currentTarget.style.background = "#003366")
            }
          >
            📄 Ver informe completo
          </button>
        </div>
      </div>
    </div>
  );
}
