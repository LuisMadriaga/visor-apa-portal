import React from "react";

export default function MensajeResultados() {
  return (
    <div
      style={{
        background: "#f8fafc",
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "32px 16px",
        boxSizing: "border-box",
      }}
    >
      {/* LOGO FALP */}
      <img
        src="/visor_apa_portal_2/static/img/logo_falp.png"
        alt="FALP"
        style={{
          width: "180px",
          maxWidth: "60vw",     // en móviles se adapta
          marginBottom: "32px",
          opacity: 0.9,
        }}
      />

      {/* CARD PRINCIPAL */}
      <div
        style={{
          width: "100%",
          maxWidth: "580px",      // tope en escritorio
          background: "#fff",
          borderRadius: "20px",
          padding: "32px 24px",
          boxShadow: "0px 10px 40px rgba(0, 0, 0, 0.08)",
          textAlign: "center",
          boxSizing: "border-box",
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
            margin: "0 auto 24px auto",
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

        {/* TÍTULO */}
        <h2
          style={{
            fontWeight: 600,
            // responsivo: mínimo 1.1rem, ideal 2.4vw, máximo 1.4rem
            fontSize: "clamp(1.1rem, 2.4vw, 1.4rem)",
            marginBottom: "10px",
            color: "#0f172a",
          }}
        >
          No se encontraron informes para el paciente.
        </h2>

        {/* SUBTÍTULO */}
        <p
          style={{
            color: "#64748b",
            fontSize: "clamp(0.9rem, 2.1vw, 1rem)",
            marginBottom: 0,
          }}
        >
          Vuelve a intentarlo más tarde.
        </p>
      </div>
    </div>
  );
}
