# Test script to simulate CH flow for TALLADORA/AFEITADORA in Ignition
# Usage: run this in the Ignition Script Console or as a gateway script.
# Edit the variables in the CONFIG section below to match your dev environment, then run.

# CONFIG
celula = "142C"          # Use celula 142C for R544000
num = None                # Auto-resolve from tags by machine Tipo
tipoMaq = "TALLADORA"    # Force TALLADORA to test CH flow
referencia = "R544000"  # Force referencia R544000 for this check
tarea = "CH"             # Force CH tarea
elemento = ""
manual = 0

# Database and table names (directly from constantes.py)
LINEA = "G_PILOT"
DATABASE_TAREAS = "GPILOT2"
TAG_PROVIDER = "[G-PILOT_TAGS]"
TABLA_RESUMEN = LINEA + "_Tareas_Resumen"
TABLA_COMPLETADOS = LINEA + "_Completados"

# Pre-define to ensure availability in finally block
original_gf = None
simulate_flag = False

# Make constantes globally available for Tareas functions
# Inject into __builtin__ so all modules can access it (Jython way)
class _Constants:
    LINEA = LINEA
    Database_Tareas = DATABASE_TAREAS
    tag_provider = TAG_PROVIDER
    celulaLinea = "142"  # Add missing attribute

constantes_obj = _Constants()
globals()['constantes'] = constantes_obj

# Also try to set in __builtin__ for Jython compatibility
try:
    import __builtin__
    __builtin__.constantes = constantes_obj
except:
    pass

# Validate environment: system and Tareas must be available (Ignition-specific)
try:
    if 'system' not in dir():
        print "[TEST] ERROR: 'system' not in environment. Run from Ignition Script Console."
        raise NameError("system not available")
    if 'Tareas' not in dir():
        print "[TEST] ERROR: 'Tareas' not in environment. Ensure Tareas module is imported."
        raise NameError("Tareas not available")
except NameError as ne:
    print "[TEST] FATAL: " + str(ne)
    raise

def _resolve_num_from_tipo(tp, celula, tipo_objetivo):
    """Find Maq_N by reading each Maq_N/Tipo and matching tipo_objetivo."""
    tipo_objetivo_up = str(tipo_objetivo).upper()
    for n in range(1, 9):
        try:
            tipo_path = tp + "Datos_Celula/Celula" + celula + "/Maq_" + str(n) + "/Tipo"
            v = system.tag.readBlocking([tipo_path])[0].value
            if v is not None and str(v).upper() == tipo_objetivo_up:
                return n
        except:
            pass
    return None

# Skip auto-detect: all values are forced
print "[TEST] Using FORCED values (no auto-detect):"
print "[TEST]   celula=%s, referencia=%s, tipoMaq=%s, num=%s, tarea=%s" % (celula, referencia, tipoMaq, str(num), tarea)

try:
    tp = TAG_PROVIDER
    # Resolve machine number from live tags first (more reliable than fixed map)
    num_real = _resolve_num_from_tipo(tp, celula, tipoMaq)
    if num_real is not None:
        num = num_real
        print "[TEST] Resolved num=%d from tags for tipoMaq=%s" % (num, tipoMaq)
    elif num is None:
        # Fallback map if tags cannot be read
        maq_map = {"TORNO": 1, "TALLADORA": 6, "AFEITADORA": 7, "RECTIFICADORA": 8}
        num = maq_map.get(tipoMaq, 6)
        print "[TEST] Fallback num=%d for tipoMaq=%s" % (num, tipoMaq)
    
    flag_path = tp + "Datos_Celula/Celula" + celula + "/Maq_" + str(num) + "/FlagCH"
    flag_tag = [flag_path]

    print "[TEST] Setting FlagCH = True -> ", flag_path
    try:
        system.tag.writeBlocking(flag_tag, [True])
        print "[TEST] FlagCH tag written successfully"
    except Exception as e:
        # Tag may not exist on this cell/machine combination; fall back to simulated flag
        print "[TEST] FlagCH write failed (tag missing?) - will simulate FlagCH for test:", e
        simulate_flag = True
        # Try to infer a valid celula/maquina from the DB for this referencia
        try:
            q = """
            SELECT TOP 1 celula, maquina FROM {0} WHERE referencia = ? AND activo = 1 ORDER BY id DESC
            """.format(TABLA_RESUMEN)
            rows = system.db.runPrepQuery(q, [referencia], DATABASE_TAREAS)
            if rows and len(rows) > 0:
                inferred_celula = rows[0][0]
                inferred_maquina = rows[0][1]
                print "[TEST] Inferred celula=%s, maquina=%s from DB for referencia=%s" % (inferred_celula, inferred_maquina, referencia)
                celula = inferred_celula
                tipoMaq = inferred_maquina
        except Exception as e2:
            print "[TEST] DB lookup for inference failed:", e2

    # NOTE: Do NOT patch GearFlow here. The script will call the real
    # Tareas.Data.GearFlow.cambioHerramientas(...) and expect a genuine
    # response (e.g. 'OK') from the service. This respects the request
    # to run the check without forcing GearFlow.

    # Emulate the CH handling that runs in DesviacionTareas for a single machine
    if simulate_flag:
        print "[TEST] Using simulated FlagCH=True"
        flag_val = True
    else:
        try:
            flag_val = bool(system.tag.readBlocking(flag_tag)[0].value)
        except Exception as e:
            print "[TEST] Error reading FlagCH:", e
            flag_val = False

    if flag_val:
        print "[TEST] FlagCH is True, checking GearFlow..."
        try:
            gf = Tareas.Data.GearFlow.cambioHerramientas(system.date.now(), tipoSolicitud="CONTROL", referencia=referencia, celula=celula, herramienta=tipoMaq)
        except Exception:
            gf = None
        if not gf:
            try:
                gf = Tareas.Data.GearFlow.cambioHerramientas(system.date.now(), tipoSolicitud="HERRAMIENTA", referencia=referencia, celula=celula, herramienta=tipoMaq)
            except Exception:
                gf = None

        print "[TEST] GearFlow returned:", gf
        if gf == 'OK':
            print "[TEST] Completing task via Tareas.Secuencia.General.completarTarea(...)"
            try:
                Tareas.Secuencia.General.completarTarea(celula, referencia, tipoMaq, tarea, num, manual)
            except Exception as e:
                print "[TEST] completarTarea raised:", e

            # Also call completarTareaBD to force DB insertion (it will validate resumen existence)
            try:
                print "[TEST] Calling completarTareaBD with:"
                print "[TEST]   celula=%s, referencia=%s, tipoMaq=%s, tarea=%s, elemento=%s, manual=%s" % (celula, referencia, tipoMaq, tarea, elemento, manual)
                res_bd = Tareas.Data.General.completarTareaBD(celula, referencia, tipoMaq, tarea, elemento, manual)
                print "[TEST] completarTareaBD returned:", res_bd
            except Exception as e:
                print "[TEST] completarTareaBD raised:", e
                import traceback
                traceback.print_exc()

            # Clear the flag
            try:
                system.tag.writeBlocking(flag_tag, [False])
                print "[TEST] FlagCH cleared"
            except Exception as e:
                print "[TEST] Error clearing FlagCH:", e
        else:
            print "[TEST] GearFlow not OK - leaving task frozen and FlagCH=True"
    else:
        print "[TEST] FlagCH was not set; nothing to do."

    # Verify DB: look for resumen id and latest completado
    try:
        db = DATABASE_TAREAS
        tablaResumen = TABLA_RESUMEN
        tablaComp = TABLA_COMPLETADOS

        # Search by celula, referencia, maquina and a CH task
        q_id = """
        SELECT TOP 1 id FROM {0} WHERE celula = ? AND referencia = ? AND maquina = ? AND activo = 1 ORDER BY id DESC
        """.format(tablaResumen)
        id_rows = system.db.runPrepQuery(q_id, [celula, referencia, tipoMaq], db)
        if id_rows and len(id_rows) > 0:
            idR = id_rows[0][0]
            print "[TEST] Found resumen id:", idR
            
            # Query with more details for verification
            q_comp = """
            SELECT TOP 1 id, fecha, manual, idUsuario, InicioFin, idTareasR 
            FROM {0} 
            WHERE idTareasR = ? 
            ORDER BY id DESC
            """.format(tablaComp)
            comp_rows = system.db.runPrepQuery(q_comp, [idR], db)
            
            if comp_rows and len(comp_rows) > 0:
                comp_id = comp_rows[0][0]
                comp_fecha = comp_rows[0][1]
                comp_manual = comp_rows[0][2]
                comp_user = comp_rows[0][3]
                comp_iniciofin = comp_rows[0][4]
                comp_tareas_r = comp_rows[0][5]
                
                print "[TEST] SUCCESS: Task completed and inserted in DB!"
                print "[TEST] ========== REGISTRO GUARDADO =========="
                print "[TEST] Tabla: %s" % tablaComp
                print "[TEST] ID Completado: %d" % comp_id
                print "[TEST] Fecha: %s" % comp_fecha
                print "[TEST] Manual: %d" % comp_manual
                print "[TEST] IdUsuario: %s" % comp_user
                print "[TEST] InicioFin: %d (1=completado)" % comp_iniciofin
                print "[TEST] idTareasR (FK): %d" % comp_tareas_r
                print "[TEST] ========================================"
            else:
                print "[TEST] WARNING: resumen found but no completado entry (completarTareaBD may have failed or not executed)"
        else:
            print "[TEST] No resumen row found for (celula, referencia, maquina). Checking available rows..."
            q_check = """
            SELECT TOP 5 id, celula, referencia, maquina FROM {0} WHERE referencia = ? ORDER BY id DESC
            """.format(tablaResumen)
            check_rows = system.db.runPrepQuery(q_check, [referencia], db)
            print "[TEST] Available rows for referencia=%s:" % referencia, check_rows
    except Exception as e:
        print "[TEST] DB verification error:", e

except Exception as e:
    print "[TEST] ERROR in main block:", str(e)
    import traceback
    traceback.print_exc()
finally:
    # Restore GearFlow
    if original_gf is not None:
        try:
            Tareas.Data.GearFlow.cambioHerramientas = original_gf
            print "[TEST] Restored original GearFlow.cambioHerramientas"
        except Exception as e:
            print "[TEST] Could not restore GearFlow:", str(e)
    
    print "[TEST] Finished"
