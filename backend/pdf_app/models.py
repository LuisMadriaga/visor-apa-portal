from django.db import models
from django.utils import timezone


class LogAcceso(models.Model):
    """
    Registro de cada intento de acceso a la aplicación (token válido o no).
    Permite auditar cuándo, desde dónde y con qué token se intentó ingresar.
    """
    rut_paciente = models.CharField(max_length=15, null=True, blank=True)
    token_hash = models.CharField(max_length=128)
    ip = models.GenericIPAddressField()
    user_agent = models.TextField(null=True, blank=True)
    estado = models.CharField(
        max_length=20,
        choices=[
            ("OK", "Acceso exitoso"),
            ("FAIL", "Token inválido o expirado"),
            ("EXPIRED", "Token expirado"),
        ],
        default="OK",
    )
    fecha_acceso = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "visor_log_acceso"
        verbose_name = "Log de Acceso"
        verbose_name_plural = "Logs de Acceso"
        ordering = ["-fecha_acceso"]

    def __str__(self):
        return f"{self.fecha_acceso} | {self.rut_paciente or 'Desconocido'} | {self.estado}"


class LogVisualizacion(models.Model):
    """
    Registro de la visualización o descarga de informes PDF.
    Permite trazabilidad de qué documento fue abierto por qué usuario (RUT).
    """
    rut_paciente = models.CharField(max_length=15)
    token_hash = models.CharField(max_length=128)
    ip = models.GenericIPAddressField()
    user_agent = models.TextField(null=True, blank=True)
    documento_id = models.CharField(max_length=50)
    fecha_visualizacion = models.DateTimeField(default=timezone.now)
    accion = models.CharField(max_length=30, default="VISUALIZACION_PDF")

    class Meta:
        db_table = "visor_log_visualizacion"
        verbose_name = "Log de Visualización"
        verbose_name_plural = "Logs de Visualización"
        ordering = ["-fecha_visualizacion"]

    def __str__(self):
        return f"{self.fecha_visualizacion} | {self.rut_paciente} | {self.documento_id}"
