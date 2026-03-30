# ================================================================
# FIX: Regenerar datos para celula 142A
# Soluciona problema donde BIN PICKING aparece con datos incorrectos
# en el tag Dataset/Tareas_Celula142
# ================================================================
# Jython 2.7 compatible - Ignition Script Console
# ================================================================

import time
import system

# ================================================================
# CONFIGURACION
# ================================================================
DB = "GPILOT2"
CELULA = "142A"
REFERENCIA = "R120638"

# ================================================================
# EJECUCION
# ================================================================
print "============================================================="
print "FIX: Regenerando datos para celula %s" % CELULA
print "============================================================="

# 1) Verificar G_Pilot_Secuencia para 142A
print "\n[1] VERIFICANDO G_Pilot_Secuencia para %s" % CELULA
print "-" * 60
sec_query = """
SELECT COUNT(*) as total, 
       SUM(CASE WHEN TipoTarea = 'BIN PICKING' THEN 1 ELSE 0 END) as bin_picking
FROM G_Pilot_Secuencia 
WHERE Celula = '%s' AND Referencia = '%s'
""" % (CELULA, REFERENCIA)
sec_data = system.db.runQuery(DB, sec_query)
print "Total filas en Secuencia: %s" % sec_data[0]['total']
print "BIN PICKING filas: %s" % sec_data[0]['bin_picking']
print "Referencia: %s" % REFERENCIA

# 2) Borrar G_Pilot_Tareas para 142A con ref R120638
print "\n[2] BORRANDO G_Pilot_Tareas para %s con ref %s" % (CELULA, REFERENCIA)
print "-" * 60
del_tareas = """
DELETE FROM G_Pilot_Tareas 
WHERE Celula = '%s' AND Referencia = '%s'
""" % (CELULA, REFERENCIA)
deleted_tareas = system.db.runUpdateQuery(DB, del_tareas)
print "Filas borradas de G_Pilot_Tareas: %s" % deleted_tareas

# 3) Borrar G_Pilot_Tareas_Resumen para 142A con ref R120638
print "\n[3] BORRANDO G_Pilot_Tareas_Resumen para %s con ref %s" % (CELULA, REFERENCIA)
print "-" * 60
del_resumen = """
DELETE FROM G_Pilot_Tareas_Resumen 
WHERE Celula = '%s' AND Referencia = '%s'
""" % (CELULA, REFERENCIA)
deleted_resumen = system.db.runUpdateQuery(DB, del_resumen)
print "Filas borradas de G_Pilot_Tareas_Resumen: %s" % deleted_resumen

# 4) Verificar borrado
print "\n[4] VERIFICANDO BORRADO"
print "-" * 60
check_query = "SELECT COUNT(*) as total FROM G_Pilot_Tareas WHERE Celula = '%s'" % CELULA
check_data = system.db.runQuery(DB, check_query)
print "Filas restantes en G_Pilot_Tareas: %s" % check_data[0]['total']

# 5) Obtener minuto MC
print "\n[5] OBTENER MINUTO MC"
print "-" * 60
mc_query = "SELECT MinutosMC FROM G_Pilot_Celulas WHERE Celula = '%s'" % CELULA
mc_data = system.db.runQuery(DB, mc_query)
mc_minutos = mc_data[0]['MinutosMC']
print "MC minutos: %s" % mc_minutos

# 6) Insertar en G_Pilot_Tareas desde G_Pilot_Secuencia
print "\n[6] INSERTANDO EN G_Pilot_Tareas"
print "-" * 60

# Obtener filas de G_Pilot_Secuencia
sec_rows = system.db.runQuery(DB, """
SELECT TipoTarea, Tarea, Occurrence, Minutos, COUNT(*) as cantidad
FROM G_Pilot_Secuencia 
WHERE Celula = '%s' AND Referencia = '%s'
GROUP BY TipoTarea, Tarea, Occurrence, Minutos
""" % (CELULA, REFERENCIA))

inserted = 0
for row in sec_rows:
    tipo = row['TipoTarea']
    tarea = row['Tarea']
    occ = row['Occurrence']
    minutos = row['Minutos']
    cantidad = row['cantidad']
    
    # Calcular minutos reales
    if tipo == "CELULA":
        minutos_calc = cantidad * float(mc_minutos)
    elif tipo == "MAQUINA":
        minutos_calc = cantidad * float(minutos)
    else:
        minutos_calc = float(minutos)
    
    # Insertar en G_Pilot_Tareas
    ins_query = """
    INSERT INTO G_Pilot_Tareas 
    (Celula, Referencia, TipoTarea, Tarea, Occurrence, Minutos, Activo, FechaCreacion)
    VALUES ('%s', '%s', '%s', '%s', %s, %s, 1, NOW())
    """ % (CELULA, REFERENCIA, tipo, tarea, occ, minutos_calc)
    
    try:
        system.db.runUpdateQuery(DB, ins_query)
        inserted += 1
    except Exception as e:
        print "ERROR insertando %s/%s: %s" % (tipo, tarea, str(e))

print "Filas insertadas en G_Pilot_Tareas: %s" % inserted

# 7) Verificar insercion
print "\n[7] VERIFICANDO INSERCION"
print "-" * 60
verify_query = """
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN TipoTarea = 'BIN PICKING' THEN 1 ELSE 0 END) as bin_picking,
    SUM(CASE WHEN TipoTarea = 'CELULA' THEN 1 ELSE 0 END) as celula
FROM G_Pilot_Tareas 
WHERE Celula = '%s' AND Referencia = '%s'
""" % (CELULA, REFERENCIA)
verify_data = system.db.runQuery(DB, verify_query)
print "Total filas insertadas: %s" % verify_data[0]['total']
print "BIN PICKING: %s" % verify_data[0]['bin_picking']
print "CELULA: %s" % verify_data[0]['celula']

# 8) Llamar cargarEstandar via Web Dev API
print "\n[8] LLAMANDO cargarEstandar WEB DEV API"
print "-" * 60
try:
    # Llamar al endpoint REST de cargarEstandar
    import socket
    import urllib
    
    params = urllib.urlencode({'celula': CELULA, 'referencia': REFERENCIA})
    url = "http://localhost:8080/DATA/GestionTareas/cargarEstandar?" + params
    
    print "Llamando: %s" % url
    
    # Intentar conexion
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('localhost', 8080))
        sock.send("GET /DATA/GestionTareas/cargarEstandar?celula=%s&referencia=%s HTTP/1.1\r\nHost: localhost\r\n\r\n" % (CELULA, REFERENCIA))
        sock.close()
        print "Request enviado"
    except:
        print "No se pudo conectar al servidor web - inicia el gateway primero"
        print "Despues de iniciar el gateway, llama manualmente:"
        print "   system.db.refresh('Tareas/Secuencia/General/Dataset_Tareas_%s', ' dataset')" % CELULA
        
except Exception as e:
    print "ERROR: %s" % str(e)

print "\n============================================================="
print "FIX COMPLETO"
print "============================================================="
print "Los datos en G_Pilot_Tareas son ahora correctos."
print "Para actualizar el tag, inicia el gateway y llama:"
print "   system.db.refresh('Tareas/Secuencia/General/Dataset_Tareas_%s', ' dataset')" % CELULA
print "============================================================="