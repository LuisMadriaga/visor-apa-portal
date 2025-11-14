import React from "react";

export default function MensajeResultados() {
  const volverInicio = () => {
    window.location.href = "https://www.falp.org/";
  };

  return (
    <div
      style={{
        background: "#f8fafc",
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        paddingTop: "40px",
      }}
    >
      {/* LOGO FALP */}
      <img
        src="/visor_apa_portal_2/static/img/logo_falp.png"
        alt="FALP"
        style={{
          width: "180px",
          marginBottom: "40px",
          opacity: 0.9,
        }}
      />

      {/* CARD PRINCIPAL */}
      <div
        style={{
          width: "100%",
          maxWidth: "580px",
          background: "#fff",
          borderRadius: "20px",
          padding: "50px 40px",
          boxShadow: "0px 10px 40px rgba(0, 0, 0, 0.08)",
          textAlign: "center",
          position: "relative",
        }}
      >
        {/* ÍCONO */}
        <div
          style={{
            width: "58px",
            height: "58px",
            borderRadius: "12px",
            background: "#f8fafc",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            margin: "0 auto 25px auto",
            border: "1px solid #e2e8f0",
          }}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#475569"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 12v.01" />
            <path d="M10 3h4l6 6v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V9z" />
          </svg>
        </div>

        {/* TITULO */}
        <h2
          style={{
            fontWeight: 600,
            fontSize: "1.2rem",
            marginBottom: "10px",
            color: "#0f172a",
          }}
        >
          No se encontraron informes para el paciente.
        </h2>

        {/* SUBTITULO */}
        <p
          style={{
            color: "#64748b",
            fontSize: "0.95rem",
            marginBottom: "20px",
          }}
        >
          Vuelve a intentarlo más tarde.
        </p>

        {/* BOTÓN — VOLVER AL INICIO */}
        <button
          onClick={volverInicio}
          style={{
            marginTop: "25px",
            background: "#f1f5f9",
            color: "#1e293b",
            border: "1px solid #cbd5e1",
            padding: "10px 18px",
            fontSize: "0.95rem",
            borderRadius: "10px",
            cursor: "pointer",
            transition: "0.2s",
          }}
        >
          Volver al Inicio
        </button>
      </div>
    </div>
  );
}
