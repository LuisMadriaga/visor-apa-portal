# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # PDFs (ya existentes)
    path("api/pdf/v2/<str:token>/", views.generar_pdf_token, name="pdf_token"),
    path("api/pdf/<str:rut>/<str:numero_biopsia>/", views.generar_pdf, name="generar_pdf"),
    
    # Informes (ya existente)
    path("api/informes-list/<str:rut>/", views.listar_informes, name="listar_informes"),
    
    # 🔹 NUEVOS ENDPOINTS
    path("api/generate-access-token/", views.generate_access_token, name="generate_access_token"),
    path("api/validate-access/", views.validate_access_token, name="validate_access"),
]
