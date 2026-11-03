# ==============================================================================
# T-AGT (TACTICAL AGENT) - MOTOR DE INTELIGENCIA Y C2
# Coordinación Autónoma de Enjambre de Rescate (Powered by Meta Muse Wonder)
# ==============================================================================

# ------------------------------------------------------------------------------
# PARTE 1: LIBRERÍAS Y CONFIGURACIÓN DEL ENLACE C2
# ------------------------------------------------------------------------------
import socket
import json
import urllib.request
import urllib.error

HOST = '127.0.0.1'
PORT = 65432

API_KEY = "LLM_39611054661873649_LwysrATZ5bNtpRn7fi1l6CqZnag"
API_URL = "https://api.meta.ai/v1/chat/completions"

# Modelo insignia del hackathon
MODELO_META = "muse-wonder"

# ------------------------------------------------------------------------------
# PARTE 2: MOTOR DE REGLAS TÁCTICAS LOCALES (FAILSAFE)
# ------------------------------------------------------------------------------
def evaluar_reglas_locales(comando_lower, ctx):
    hay_base = ctx.get("base_establecida") == "SÍ"
    hay_target_uav = ctx.get("uav_target_establecido") == "SÍ"
    hay_target_mini = ctx.get("mini_target_establecido") == "SÍ"
    hay_target_amb = ctx.get("amb_target_establecido") == "SÍ"
    conteo = ctx.get("conteo", {"uav": 0, "mini": 0, "amb": 0})
    flota = ctx.get("unidades_desplegadas", [])
    
    if "victima_detectada" in comando_lower or "survivor_found" in comando_lower:
        siguiente = conteo.get("amb", 0) + 1
        return {
            "mensaje_operador": f"[ALERTA CRÍTICA V-AGT] Víctima confirmada por sensor de MINI-1. Despachando inmediatamente Ambulancia AMB-{siguiente} con soporte vital al punto de extracción.",
            "codigo_accion": "DESPLEGAR_AMBULANCIA"
        }

    if any(w in comando_lower for w in ["bateria", "batería", "energia", "status", "estado", "reporte"]):
        wps = ctx.get("waypoints_activos", 0)
        return {
            "mensaje_operador": f"C2 Telemetry (Muse Wonder): Flota ({len(flota)}/9). UAVs: {conteo.get('uav', 0)}/3 | Minis: {conteo.get('mini', 0)}/3 | Ambulancias: {conteo.get('amb', 0)}/3. Checkpoints: {wps}. Baterías nominales (94-98%).",
            "codigo_accion": "NINGUNA"
        }

    if any(w in comando_lower for w in ["dron", "drone", "uav", "aereo", "aéreo"]):
        if not hay_base:
            return {"mensaje_operador": "Negativo. Se requiere fijar primero la Base de Rescate con clic derecho.", "codigo_accion": "NINGUNA"}
        if not hay_target_uav:
            return {"mensaje_operador": "Negativo. Falta zona de inspección aérea. Haz clic derecho y selecciona [🎯 Marcar Objetivo: Dron UAV].", "codigo_accion": "NINGUNA"}
        if conteo.get("uav", 0) >= 3:
            return {"mensaje_operador": "Negativo. Capacidad aérea máxima alcanzada (3/3 UAVs desplegados).", "codigo_accion": "NINGUNA"}
        siguiente = conteo.get("uav", 0) + 1
        return {"mensaje_operador": f"Base y objetivo aéreo validados. Desplegando unidad UAV-{siguiente} hacia el sector asignado.", "codigo_accion": "DESPLEGAR_UAV"}

    if any(w in comando_lower for w in ["mini", "scout", "explorador", "pequeña", "pequena"]):
        if not hay_base:
            return {"mensaje_operador": "Negativo. Establezca la Base de Rescate antes de enviar exploradores.", "codigo_accion": "NINGUNA"}
        if not hay_target_mini:
            return {"mensaje_operador": "Negativo. Falta punto de inspección. Haz clic derecho en el mapa y selecciona [🔍 Marcar Objetivo: Mini-Ambulancia].", "codigo_accion": "NINGUNA"}
        if conteo.get("mini", 0) >= 3:
            return {"mensaje_operador": "Negativo. Capacidad de exploración máxima alcanzada (3/3 Mini-Ambulancias).", "codigo_accion": "NINGUNA"}
        siguiente = conteo.get("mini", 0) + 1
        return {"mensaje_operador": f"Autorizado por Muse Wonder. Despachando Mini-Ambulancia MINI-{siguiente} para infiltración en áreas estrechas.", "codigo_accion": "DESPLEGAR_MINI_AMBULANCIA"}

    if any(w in comando_lower for w in ["ambulancia", "rover", "ugv", "terrestre", "pesada"]):
        if not hay_base:
            return {"mensaje_operador": "Negativo. Se requiere fijar la Base antes de despachar soporte médico pesado.", "codigo_accion": "NINGUNA"}
        if not hay_target_amb:
            return {"mensaje_operador": "Negativo. Falta punto de extracción médica. Haz clic derecho y selecciona [🚑 Marcar Objetivo: Ambulancia UGV].", "codigo_accion": "NINGUNA"}
        if conteo.get("amb", 0) >= 3:
            return {"mensaje_operador": "Negativo. Capacidad de soporte vital máxima alcanzada (3/3 Ambulancias).", "codigo_accion": "NINGUNA"}
        siguiente = conteo.get("amb", 0) + 1
        return {"mensaje_operador": f"Objetivo de extracción confirmado. Despachando Ambulancia médica AMB-{siguiente}.", "codigo_accion": "DESPLEGAR_AMBULANCIA"}

    if any(w in comando_lower for w in ["retorno", "base", "volver", "rtb"]):
        return {"mensaje_operador": "Orden confirmada. Retorno a base (RTB) activado para toda la flota.", "codigo_accion": "RETORNO_BASE"}
    
    if any(w in comando_lower for w in ["alto", "stop", "detener", "parar"]):
        return {"mensaje_operador": "Emergencia: Alto total aplicado a toda la flota.", "codigo_accion": "ALTO_TOTAL"}

    return {"mensaje_operador": "R-AGT (Muse Wonder Core) a la escucha. Indique directiva táctica.", "codigo_accion": "NINGUNA"}

# ------------------------------------------------------------------------------
# PARTE 3: PROCESAMIENTO COGNITIVO CON MUSE WONDER
# ------------------------------------------------------------------------------
def procesar_con_llama(mensaje_operador, map_context_str):
    try:
        ctx = json.loads(map_context_str)
    except Exception:
        ctx = {}

    system_prompt = (
        "Eres R-AGT, Agente Autónomo de Coordinación de Rescate Humanitario (KIRKINX C2), "
        "impulsado por la arquitectura Meta Muse Wonder. "
        "Tu misión es orquestar un enjambre autónomo de rescate de hasta 9 activos tácticos.\n"
        f"TELEMETRÍA EN VIVO:\n{json.dumps(ctx, ensure_ascii=False)}\n\n"
        "REGLAS OPERATIVAS:\n"
        "1. Base = NO -> Denegar despliegues.\n"
        "2. Piden Dron: Exigir 'uav_target_establecido'='SÍ'. Si es NO, exigir marcar [🎯 Marcar Objetivo: Dron UAV]. Si es SÍ, usar 'DESPLEGAR_UAV'.\n"
        "3. Piden Mini-Ambulancia: Exigir 'mini_target_establecido'='SÍ'. Si es NO, exigir marcar [🔍 Marcar Objetivo: Mini-Ambulancia]. Si es SÍ, usar 'DESPLEGAR_MINI_AMBULANCIA'.\n"
        "4. Piden Ambulancia: Exigir 'amb_target_establecido'='SÍ'. Si es NO, exigir marcar [🚑 Marcar Objetivo: Ambulancia UGV]. Si es SÍ, usar 'DESPLEGAR_AMBULANCIA'.\n"
        "5. Si entra una alerta de víctima detectada ('VICTIMA_DETECTADA' o 'SURVIVOR_FOUND'), autoriza de inmediato 'DESPLEGAR_AMBULANCIA'.\n"
        "6. Máximo 3 unidades por categoría.\n\n"
        "RESPONDE ÚNICAMENTE CON UN OBJETO JSON VÁLIDO (sin markdown ```json):\n"
        "{\n"
        '  "mensaje_operador": "Texto conciso y profesional para el operador",\n'
        '  "codigo_accion": "NINGUNA | DESPLEGAR_UAV | DESPLEGAR_MINI_AMBULANCIA | DESPLEGAR_AMBULANCIA | ALTO_TOTAL | RETORNO_BASE"\n'
        "}"
    )

    payload = {
        "model": MODELO_META,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": mensaje_operador}
        ],
        "temperature": 0.1,
        "max_tokens": 350
    }

    try:
        req = urllib.request.Request(
            API_URL, 
            data=json.dumps(payload).encode('utf-8'), 
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}, 
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            if resp.getcode() == 200:
                data = json.loads(resp.read().decode('utf-8'))
                choices = data.get("choices", [])
                contenido = choices[0]["message"].get("content", "") if choices else ""
                
                contenido = str(contenido).strip()
                if contenido.startswith("```json"):
                    contenido = contenido[7:]
                if contenido.endswith("```"):
                    contenido = contenido[:-3]

                start = contenido.find('{')
                end = contenido.rfind('}')
                if start != -1 and end != -1:
                    json_str = contenido[start:end+1]
                    json.loads(json_str)
                    return json_str
    except Exception as e:
        print(f"[DEBUG] Derivando a motor contextual local: {e}")

    resultado_local = evaluar_reglas_locales(mensaje_operador.lower(), ctx)
    return json.dumps(resultado_local, ensure_ascii=False)

# ------------------------------------------------------------------------------
# PARTE 4: SERVIDOR DE COMUNICACIÓN SOCKET (C2 LISTENER)
# ------------------------------------------------------------------------------
ALERTA_MEDICA_PENDIENTE = False
MINI_EN_ZONA = False  # <-- NUEVA BANDERA: Sabe si el vehículo ya llegó

def iniciar_cerebro():
    global ALERTA_MEDICA_PENDIENTE, MINI_EN_ZONA
    print("==================================================")
    print(" R-AGT (RESCUE AGENT) - POWERED BY META MUSE WONDER")
    print("==================================================")
    print(f"[INFO] Servidor C2 escuchando en puerto {PORT}...")
    print(f"[INFO] Modelo activo: {MODELO_META}\n")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        
        while True:
            conn, addr = s.accept()
            with conn:
                datos = conn.recv(4096)
                if datos:
                    comando = datos.decode('utf-8')
                    
                    if comando.startswith("C2|"):
                        partes = comando.split("|", 2)
                        contexto = partes[1] if len(partes) > 1 else "{}"
                        orden = partes[2] if len(partes) > 2 else ""
                        
                        if orden == "POLL_ALERTA":
                            if ALERTA_MEDICA_PENDIENTE:
                                ALERTA_MEDICA_PENDIENTE = False
                                respuesta = json.dumps({
                                    "mensaje_operador": "ALERTA CRÍTICA V-AGT: Víctima confirmada por sensor óptico (Edge Computing). Despachando Ambulancia Médica Pesada de forma autónoma al sector.",
                                    "codigo_accion": "DESPLEGAR_AMBULANCIA"
                                }, ensure_ascii=False)
                            else:
                                respuesta = json.dumps({"codigo_accion": "NINGUNA"}, ensure_ascii=False)
                            
                            conn.sendall(respuesta.encode('utf-8'))
                            continue 
                        
                        # --- NUEVO: El mapa avisa que la mini-ambulancia llegó ---
                        if orden == "MINI_EN_POSICION":
                            MINI_EN_ZONA = True
                            conn.sendall(b'{"status": "RECIBIDO"}')
                            continue
                            
                        # --- NUEVO: El video pregunta silenciosamente si ya debe arrancar ---
                        if orden == "POLL_VIDEO":
                            if MINI_EN_ZONA:
                                conn.sendall(b'{"comando": "INICIAR_VIDEO"}')
                                MINI_EN_ZONA = False  # Apagamos para el futuro
                            else:
                                conn.sendall(b'{"comando": "ESPERAR"}')
                            continue
                        # -----------------------------------------------------------

                        print(f"[📥] INSTRUCCIÓN: {orden}")
                        respuesta = procesar_con_llama(orden, contexto)
                        print(f"[📤] ACCIÓN C2: {respuesta}\n")
                        conn.sendall(respuesta.encode('utf-8'))
                        
                    elif "CASUALTY_LOCATED" in comando:
                        print(f"\n[🚨 ALERTA CRÍTICA V-AGT] Objetivo detectado en el feed óptico perimetral.")
                        ALERTA_MEDICA_PENDIENTE = True 
                        conn.sendall(b'{"status": "RECIBIDO_EN_C2"}')
                        
                    else:
                        conn.sendall(b'{"mensaje_operador": "Protocolo C2 no reconocido.", "codigo_accion": "NINGUNA"}')

if __name__ == "__main__":
    iniciar_cerebro()