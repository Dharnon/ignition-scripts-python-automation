# ================================================================
# FIX: Regenerar datos para celula 142A
# Incluye G_Pilot_Tareas_Resumen
# ================================================================
# Jython 2.7 compatible - Ignition Script Console
# ================================================================

# CONFIGURACION
DB = "GPILOT2"
CELULA = "142A"
REFERENCIA = "R120638"

print "============================================================="
print "FIX: Regenerando G_Pilot_Tareas_Resumen para %s" % CELULA
print "============================================================="

# 1) Llamar a insertarTareasEnTablaResumen
print "\n[1] LLAMANDO insertarTareasEnTablaResumen"
print "-" * 60
try:
    Tareas.Data.fromExcelToDB.insertarTareasEnTablaResumen(CELULA, REFERENCIA)
    print "OK: G_Pilot_Tareas_Resumen actualizado"
except Exception as e:
    print "ERROR: %s" % str(e)

# 2) Verificar insercin
print "\n[2] VERIFICANDO G_Pilot_Tareas_Resumen"
print "-" * 60
verify_query = """
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN activo = 1 THEN 1 ELSE 0 END) as activos,
    SUM(CASE WHEN tarea = 'BIN PICKING' THEN 1 ELSE 0 END) as bin_picking,
    SUM(CASE WHEN tarea = 'CELULA' THEN 1 ELSE 0 END) as celula
FROM G_Pilot_Tareas_Resumen 
WHERE celula = '%s' AND referencia = '%s'
""" % (CELULA, REFERENCIA)
verify_data = system.db.runQuery(DB, verify_query)
print "Total filas: %s" % verify_data[0]['total']
print "Activas: %s" % verify_data[0]['activos']
print "BIN PICKING: %s" % verify_data[0]['bin_picking']
print "CELULA: %s" % verify_data[0]['celula']

# 3) Actualizar el tag
print "\n[3] ACTUALIZANDO TAG Dataset/Tareas_Celula142"
print "-" * 60
try:
    Tareas.Secuencia.General.iniciarEstandar(CELULA, REFERENCIA)
    print "OK: Tag actualizado"
except Exception as e:
    print "ERROR actualizando tag: %s" % str(e)

print "\n============================================================="
print "FIX COMPLETO"
print "============================================================="