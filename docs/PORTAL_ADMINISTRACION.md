# Portal web y administración asistida

## Objetivo

La versión 3.2 incorpora al dashboard una capa de operación para usuarios no técnicos. El portal conserva las vistas públicas de indicadores y agrega:

- calendario de fechas esperadas y estado local de cada trimestre;
- consulta manual de nuevas publicaciones en INDEC;
- prevalidación de un trimestre sin incorporarlo al histórico;
- visualización de controles, comparación histórica y alertas orientativas;
- incorporación final protegida por revisión humana, confirmación explícita y configuración de seguridad.

La lógica estadística no se duplica: el portal llama a las mismas funciones de `pipeline.py` y `monitor_actualizaciones.py`.

**Importante (v3.2.1):** la pestaña **Calendario** no verifica el sitio del INDEC. Presenta fechas esperadas y estados registrados localmente. La verificación remota del ZIP se realiza únicamente al usar **Consultar INDEC ahora** en Administración.

## Secciones del portal

1. **Resumen ejecutivo**: indicadores del último período validado.
2. **Evolución laboral**: series de actividad, empleo, desocupación e informalidad.
3. **Ingresos**: indicadores nominales y advertencias de interpretación.
4. **Calendario**: fecha esperada, estado y próximo período.
5. **Calidad y auditoría**: estados, esquema, calidad y validaciones.
6. **Documentación y descargas**: histórico, metadatos, manifiesto y guías.
7. **Administración**: monitor, prevalidación y publicación controlada.

## Seguridad del MVP

El área administrativa requiere una clave configurada fuera del código. No se incluye ninguna contraseña en el repositorio.

### Opción A — variables de entorno

Windows PowerShell:

```powershell
$env:EPH_ADMIN_PASSWORD="una-clave-segura"
$env:EPH_ADMIN_ENABLE_WRITES="1"
python -m streamlit run notebooks/app.py
```

Si se omite `EPH_ADMIN_ENABLE_WRITES`, el operador puede monitorear y prevalidar, pero no incorporar períodos al histórico desde la interfaz.

### Opción B — Streamlit secrets

Crear localmente `.streamlit/secrets.toml`:

```toml
admin_password = "una-clave-segura"
admin_enable_writes = true
```

El archivo real de secretos está ignorado por Git y no debe subirse al repositorio. Se incluye `.streamlit/secrets.toml.example` sólo como plantilla.

## Flujo de actualización desde la interfaz

```text
Calendario
   ↓
Consultar INDEC
   ↓
Nueva publicación detectada
   ↓
Prevalidar
   ↓
Controles + comparación + alertas
   ↓
Revisión humana
   ↓
Confirmar período
   ↓
Pipeline transaccional
   ↓
Histórico validado
   ↓
Snapshot actualizado
```

La prevalidación **no modifica** `historico_SDE.csv` ni `data_snapshot/`. La incorporación final vuelve a ejecutar el pipeline completo, por lo que el período debe superar nuevamente todos los controles críticos.

## Persistencia

En una instalación local o servidor de la DGEyC, `results/`, `data/` y `data_snapshot/` son persistentes en disco.

En servicios con sistema de archivos efímero, como ciertos despliegues administrados, una modificación realizada desde la interfaz puede perderse al reiniciar la instancia. En ese caso, el portal puede mantenerse en modo consulta/prevalidación y la publicación final debe ejecutarse sobre infraestructura persistente.

## Alcance de la autenticación

La clave del portal es una protección adecuada para el MVP académico/institucional. Para una adopción productiva multiusuario se recomienda reemplazarla por autenticación corporativa (SSO/OIDC), roles y auditoría de usuario.
