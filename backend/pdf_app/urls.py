# from django.urls import path
# from . import views

# urlpatterns = [
#     path("api/informes-list/", views.listar_informes, name="listar_informes"),
#     path("api/informes-list/<str:rut>/", views.listar_informes, name="listar_informes_rut"),
#     path("api/pdf/<str:rut>/", views.generar_pdf, name="generar_pdf"),
#     path("api/pdf/<str:rut>/", views.generar_pdf, name="pdf_por_rut"),
#     path("api/pdf/<str:rut>/<str:biopsia>/", views.generar_pdf, name="pdf_por_biopsia"),

# ]

from django.urls import path
from . import views

urlpatterns = [
    path("api/pdf/v2/<str:token>/", views.generar_pdf_token, name="pdf_token"),
    path("api/informes-list/<str:rut>/", views.listar_informes, name="listar_informes"),
    path("api/pdf/<str:rut>/<str:numero_biopsia>/", views.generar_pdf, name="generar_pdf"),
]

