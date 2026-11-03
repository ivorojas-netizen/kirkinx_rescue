# ==============================================================================
# N-AGT (NAVIGATIONAL AGENT) - ROVER SWARM C2 SYSTEM 2.0
# Módulo de Conciencia Espacial, Blue Force Tracking y Telemetría IA
# ==============================================================================

# ------------------------------------------------------------------------------
# PARTE 1: LIBRERÍAS Y DEPENDENCIAS DEL SISTEMA
# ------------------------------------------------------------------------------
import tkinter as tk
import tkintermapview
import random
import time
import socket 
import threading 
import cv2
import json
import urllib.request
import urllib.error
import os
import numpy as np
from PIL import Image, ImageTk

# ------------------------------------------------------------------------------
# PARTE 2: CONFIGURACIÓN, SERVIDORES Y REGISTROS DEL ENJAMBRE
# ------------------------------------------------------------------------------
SERVIDOR_MAPA = "https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}"
IP_CELULAR = "192.168.1.171"

# Paleta táctica de colores
COLOR_FONDO = "#0B0E14"
COLOR_PANEL = "#161B22"
COLOR_TEXTO = "#c9d1d9"
COLOR_ROVER = "#3fb950"   # Verde: Ambulancia médica pesada
COLOR_BASE = "#1f6feb"    # Azul: Puesto de mando central
COLOR_DRON = "#00ffff"    # Cian: UAV reconocimiento aéreo
COLOR_OBJETIVO = "#f85149"# Rojo: Objetivo crítico
COLOR_MINI = "#f0883e"    # Naranja: Mini-Ambulancia scout ligera

LAT_INICIAL = -16.5190021
LON_INICIAL = -68.0459120

class AgenteNavegacion:
    def __init__(self, master):
        self.master = master
        self.master.title("N-AGT | Autonomous Rescue Swarm C2 (Meta Llama 3 Powered)")
        self.master.geometry("1100x650")
        self.master.configure(bg=COLOR_FONDO)

        # Registros del estado del enjambre
        self.flota_activa = {}
        self.marcador_base = None
        self.rutas_activas = {} 
        self.waypoints_temporales = [] 
        self.marcadores_wp = []        
        self.historial_visitados = {}
        self.sistema_pausado = False  

        # Contadores de activos del enjambre (Límite: 3 de cada tipo = 9 enjambre)
        self.conteo_uav = 0
        self.conteo_mini = 0
        self.conteo_amb = 0

        # Objetivos Tácticos Designados por el Operador
        self.target_uav = None
        self.marcador_target_uav = None
        self.target_mini = None
        self.marcador_target_mini = None
        self.target_ambulancia = None
        self.marcador_target_amb = None

        # Inicialización de subsistemas modulares
        self.construir_interfaz()
        self.iniciar_mapa()
        self.configurar_clic_derecho()
        self.motor_navegacion()
        self.iniciar_monitoreo_silencioso() # <-- LÍNEA NUEVA: Arranca el monitor automático

    # --------------------------------------------------------------------------
    # NUEVA FUNCIÓN: MONITOREO SILENCIOSO (1 Hz) PARA AUTONOMÍA
    # --------------------------------------------------------------------------
    def iniciar_monitoreo_silencioso(self):
        """Consulta silenciosamente al T-AGT a 1 Hz sin saturar el chat visual."""
        def consultar_alertas():
            if not getattr(self, 'sistema_pausado', False):
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1.0)
                        s.connect(('127.0.0.1', 65432))
                        
                        paquete = "C2|{}|POLL_ALERTA"
                        s.sendall(paquete.encode('utf-8'))
                        
                        respuesta_cruda = s.recv(4096).decode('utf-8')
                        if respuesta_cruda:
                            datos_ia = json.loads(respuesta_cruda)
                            accion = datos_ia.get("codigo_accion", "NINGUNA")
                            mensaje = datos_ia.get("mensaje_operador", "")
                            
                            if accion == "DESPLEGAR_AMBULANCIA":
                                # CORRECCIÓN: Si no marcaste el objetivo de la ambulancia pesada, 
                                # usa automáticamente las coordenadas donde ya estaba la mini-ambulancia.
                                destino = self.target_ambulancia or self.target_mini
                                
                                if destino:
                                    self.chat_display.config(state=tk.NORMAL)
                                    self.chat_display.insert(tk.END, f"[R-AGT | ALERTA AUTÓNOMA]: {mensaje}\n\n", "ia")
                                    self.chat_display.config(state=tk.DISABLED)
                                    self.chat_display.see(tk.END)
                                    
                                    self.master.after(0, lambda: self.desplegar_ambulancia_click(destino))
                except Exception:
                    pass # Falla silenciosa si no hay conexión, reintenta en el próximo segundo
            
            self.master.after(1000, consultar_alertas)

        self.master.after(1000, consultar_alertas)

    # --------------------------------------------------------------------------
    # PARTE 3: INTERFAZ GRÁFICA (PANEL LATERAL TÁCTICO Y CHAT C2)
    # --------------------------------------------------------------------------
    def construir_interfaz(self):
        self.panel_izq = tk.Frame(self.master, bg=COLOR_PANEL, width=300)
        self.panel_izq.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        self.panel_izq.pack_propagate(False)

        tk.Label(
            self.panel_izq, 
            text="[ N-AGT : BLUE FORCE TRACKING ]", 
            bg=COLOR_PANEL, 
            fg="#58a6ff", 
            font=("Consolas", 10, "bold")
        ).pack(pady=15)

        # Buscador de coordenadas o ciudades
        frame_buscador = tk.Frame(self.panel_izq, bg=COLOR_PANEL)
        frame_buscador.pack(fill=tk.X, padx=10, pady=5)
        self.entrada_busqueda = tk.Entry(frame_buscador, bg="#0d1117", fg=COLOR_TEXTO, insertbackground=COLOR_TEXTO)
        self.entrada_busqueda.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.entrada_busqueda.insert(0, "Lat,Lon o Ciudad...")
        btn_buscar = tk.Button(frame_buscador, text="🔍", bg="#238636", fg="white", bd=0, command=self.buscar_ubicacion)
        btn_buscar.pack(side=tk.RIGHT)

        # Botones de comandos globales
        frame_comandos = tk.Frame(self.panel_izq, bg=COLOR_PANEL)
        frame_comandos.pack(fill=tk.X, padx=10, pady=10)

        btn_centrar = tk.Button(
            frame_comandos, text="🎯 Centrar en Base", bg="#1f6feb", fg="white", bd=0, font=("Arial", 8, "bold"), command=self.centrar_en_base
        )
        btn_centrar.pack(fill=tk.X, pady=(0, 5))

        self.btn_stop = tk.Button(
            frame_comandos, text="🛑 ALTO TOTAL", bg="#da3633", fg="white", bd=0, font=("Arial", 8, "bold"), command=self.toggle_pausa
        )
        self.btn_stop.pack(fill=tk.X, pady=(0, 5))

        btn_rtb = tk.Button(
            frame_comandos, text="🏠 RETORNO A BASE (RTB)", bg="#e3b341", fg="black", bd=0, font=("Arial", 8, "bold"), command=self.retorno_a_base
        )
        btn_rtb.pack(fill=tk.X, pady=(0, 10))

        # Sección: Flujo de telemetría cruda
        tk.Label(
            self.panel_izq, text="TELEMETRÍA CRUDA (1 Hz):", bg=COLOR_PANEL, fg="#8b949e", font=("Arial", 8, "bold")
        ).pack(anchor="w", padx=10, pady=(5, 2))
        
        self.consola = tk.Text(
            self.panel_izq, bg="#0d1117", fg="#3fb950", font=("Consolas", 8), height=10, wrap=tk.WORD
        )
        self.consola.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Sección: Chat de enlace con el cerebro R-AGT
        tk.Label(
            self.panel_izq, text="ENLACE C2 - R-AGT (CEREBRO IA):", bg=COLOR_PANEL, fg="#d2a8ff", font=("Arial", 8, "bold")
        ).pack(anchor="w", padx=10, pady=(5, 2))
        
        self.chat_display = tk.Text(
            self.panel_izq, bg="#0d1117", fg="#c9d1d9", font=("Consolas", 9), height=12, state=tk.DISABLED, wrap=tk.WORD
        )
        self.chat_display.pack(fill=tk.X, padx=10, pady=(0, 5))
        self.chat_display.tag_config("operador", foreground="#58a6ff")
        self.chat_display.tag_config("ia", foreground="#d2a8ff")

        frame_input = tk.Frame(self.panel_izq, bg=COLOR_PANEL)
        frame_input.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.chat_input = tk.Entry(
            frame_input, bg="#0d1117", fg="#58a6ff", font=("Consolas", 9), insertbackground=COLOR_TEXTO
        )
        self.chat_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.chat_input.bind("<Return>", lambda event: self.enviar_comando_chat()) 
        
        btn_enviar = tk.Button(
            frame_input, text="ENVIAR", bg="#6e40c9", fg="white", bd=0, font=("Arial", 8, "bold"), command=self.enviar_comando_chat
        )
        btn_enviar.pack(side=tk.RIGHT)

    def enviar_comando_chat(self):
        comando = self.chat_input.get().strip()
        if not comando:
            return
        
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"[OPERADOR]: {comando}\n", "operador")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
        self.chat_input.delete(0, tk.END)

        # Inyección de telemetría completa al cerebro C2
        contexto = {
            "base_establecida": "SÍ" if self.marcador_base else "NO",
            "uav_target_establecido": "SÍ" if self.target_uav else "NO",
            "mini_target_establecido": "SÍ" if self.target_mini else "NO",
            "amb_target_establecido": "SÍ" if self.target_ambulancia else "NO",
            "waypoints_activos": len(self.waypoints_temporales),
            "unidades_desplegadas": list(self.flota_activa.keys()),
            "conteo": {
                "uav": self.conteo_uav,
                "mini": self.conteo_mini,
                "amb": self.conteo_amb
            },
            "baterias": {"UAV": "94%", "Mini": "96%", "Ambulancia": "98%"},
            "sistema_pausado": "SÍ" if getattr(self, 'sistema_pausado', False) else "NO"
        }
        contexto_str = json.dumps(contexto, ensure_ascii=False)

        def comunicar_tagt():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(20)
                    s.connect(('127.0.0.1', 65432))
                    paquete = f"C2|{contexto_str}|{comando}"
                    s.sendall(paquete.encode('utf-8'))
                    
                    respuesta_cruda = s.recv(4096).decode('utf-8')
                    try:
                        datos_ia = json.loads(respuesta_cruda)
                        mensaje = datos_ia.get("mensaje_operador", "[!] Sin reporte.")
                        accion = datos_ia.get("codigo_accion", "NINGUNA")
                        
                        self.master.after(0, lambda: _mostrar_respuesta(mensaje))
                        
                        # Ejecución autónoma según decisión de la IA
                        if accion == "DESPLEGAR_UAV":
                            if self.target_uav:
                                self.master.after(0, lambda: self.desplegar_dron_click(self.target_uav))
                            
                        elif accion == "DESPLEGAR_MINI_AMBULANCIA":
                            if self.target_mini:
                                self.master.after(0, lambda: self.desplegar_mini_ambulancia_click(self.target_mini))

                        elif accion == "DESPLEGAR_AMBULANCIA":
                            if self.target_ambulancia:
                                self.master.after(0, lambda: self.desplegar_ambulancia_click(self.target_ambulancia))

                        elif accion == "RETORNO_BASE":
                            self.master.after(0, self.retorno_a_base)

                        elif accion == "ALTO_TOTAL":
                            if not getattr(self, 'sistema_pausado', False):
                                self.master.after(0, self.toggle_pausa)

                    except json.JSONDecodeError:
                        self.master.after(0, lambda: _mostrar_respuesta(respuesta_cruda))

            except Exception as e:
                self.master.after(0, lambda: _mostrar_respuesta(f"[ERROR C2]: {str(e)}"))

        def _mostrar_respuesta(resp):
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, f"[R-AGT]: {resp}\n\n", "ia")
            self.chat_display.config(state=tk.DISABLED)
            self.chat_display.see(tk.END)

        threading.Thread(target=comunicar_tagt, daemon=True).start()

    # --------------------------------------------------------------------------
    # PARTE 4: MOTOR DE MAPAS (SATELITAL)
    # --------------------------------------------------------------------------
    def iniciar_mapa(self):
        self.frame_mapa = tk.Frame(self.master, bg=COLOR_FONDO)
        self.frame_mapa.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.mapa = tkintermapview.TkinterMapView(self.frame_mapa, corner_radius=0)
        self.mapa.pack(fill=tk.BOTH, expand=True)
        self.mapa.set_tile_server(SERVIDOR_MAPA, max_zoom=19)
        self.mapa.set_position(LAT_INICIAL, LON_INICIAL)
        self.mapa.set_zoom(17)

    # --------------------------------------------------------------------------
    # PARTE 5: MARCADORES, MENÚ CONTEXTUAL Y DESPLIEGUE MULTI-ACTIVO
    # --------------------------------------------------------------------------
    def configurar_clic_derecho(self):
        self.mapa.add_right_click_menu_command(label="📍 Establecer Base de Rescate", command=self.fijar_base_click, pass_coords=True)
        self.mapa.add_right_click_menu_command(label="🎯 Marcar Objetivo: Dron UAV", command=self.fijar_target_uav_click, pass_coords=True)
        self.mapa.add_right_click_menu_command(label="🔍 Marcar Objetivo: Mini-Ambulancia", command=self.fijar_target_mini_click, pass_coords=True)
        self.mapa.add_right_click_menu_command(label="🚑 Marcar Objetivo: Ambulancia UGV", command=self.fijar_target_amb_click, pass_coords=True)
        self.mapa.add_right_click_menu_command(label="🚩 Marcar Waypoint de Tránsito", command=self.marcar_waypoint, pass_coords=True)
        self.mapa.add_right_click_menu_command(label="❌ Borrar Todos los Puntos y Objetivos", command=self.borrar_waypoints_click, pass_coords=True)

    def fijar_base_click(self, coords):
        lat, lon = coords
        if self.marcador_base:
            self.marcador_base.delete()
        self.marcador_base = self.mapa.set_marker(lat, lon, text="BASE", marker_color_circle="black", marker_color_outside=COLOR_BASE)
        self.log_telemetria(f"BASE establecida en: {lat:.5f}, {lon:.5f}")

    def fijar_target_uav_click(self, coords):
        lat, lon = coords
        self.target_uav = (lat, lon)
        if self.marcador_target_uav:
            self.marcador_target_uav.delete()
        self.marcador_target_uav = self.mapa.set_marker(
            lat, lon, text="OBJETIVO-UAV", marker_color_circle="black", marker_color_outside=COLOR_DRON
        )
        self.log_telemetria(f"[C2] Zona de inspección para UAV fijada en: {lat:.5f}, {lon:.5f}")

    def fijar_target_mini_click(self, coords):
        lat, lon = coords
        self.target_mini = (lat, lon)
        if self.marcador_target_mini:
            self.marcador_target_mini.delete()
        self.marcador_target_mini = self.mapa.set_marker(
            lat, lon, text="OBJETIVO-MINI", marker_color_circle="black", marker_color_outside=COLOR_MINI
        )
        self.log_telemetria(f"[C2] Punto de exploración para Mini-Ambulancia fijado en: {lat:.5f}, {lon:.5f}")

    def fijar_target_amb_click(self, coords):
        lat, lon = coords
        self.target_ambulancia = (lat, lon)
        if self.marcador_target_amb:
            self.marcador_target_amb.delete()
        self.marcador_target_amb = self.mapa.set_marker(
            lat, lon, text="OBJETIVO-AMB", marker_color_circle="black", marker_color_outside=COLOR_OBJETIVO
        )
        self.log_telemetria(f"[C2] Punto de extracción médica para Ambulancia fijado en: {lat:.5f}, {lon:.5f}")

    def borrar_waypoints_click(self, coords):
        for wp in self.marcadores_wp:
            wp.delete()
        self.marcadores_wp = []
        self.waypoints_temporales = []
        
        if self.marcador_target_uav:
            self.marcador_target_uav.delete()
            self.marcador_target_uav = None
            self.target_uav = None
            
        if self.marcador_target_mini:
            self.marcador_target_mini.delete()
            self.marcador_target_mini = None
            self.target_mini = None

        if self.marcador_target_amb:
            self.marcador_target_amb.delete()
            self.marcador_target_amb = None
            self.target_ambulancia = None

        self.log_telemetria("[RUTAS] Objetivos y waypoints purgados del mapa.")

    def marcar_waypoint(self, coords):
        lat, lon = coords
        def borrar_este_wp(marcador):
            marcador.delete()
            if marcador in self.marcadores_wp:
                self.marcadores_wp.remove(marcador)
            lat_m, lon_m = marcador.position
            self.waypoints_temporales = [wp for wp in self.waypoints_temporales if wp != (lat_m, lon_m)]
            self.log_telemetria("[RUTAS] Waypoint borrado unitariamente.")

        self.waypoints_temporales.append((lat, lon))
        wp = self.mapa.set_marker(
            lat, lon, text=f"WP-{len(self.waypoints_temporales)}", 
            marker_color_circle="black", marker_color_outside="#8b949e", command=borrar_este_wp
        )
        self.marcadores_wp.append(wp)
        self.log_telemetria(f"[RUTAS] Waypoint-{len(self.waypoints_temporales)} registrado.")

    def desplegar_dron_click(self, coords):
        if self.conteo_uav >= 3:
            self.log_telemetria("[ALERTA] Capacidad máxima alcanzada: 3 UAVs en vuelo.")
            return

        self.conteo_uav += 1
        id_dron = f"UAV-{self.conteo_uav}"
        lat, lon = coords
        
        inicio_lat = self.marcador_base.position[0] if self.marcador_base else LAT_INICIAL
        inicio_lon = self.marcador_base.position[1] if self.marcador_base else LON_INICIAL

        self.flota_activa[id_dron] = self.mapa.set_marker(
            inicio_lat, inicio_lon, text=id_dron, 
            marker_color_circle="black", marker_color_outside=COLOR_DRON, 
            command=self.abrir_feed_video
        )

        vector_aereo = [(inicio_lat, inicio_lon), (lat, lon)]
        linea_vuelo = self.mapa.set_path(vector_aereo, color=COLOR_DRON, width=2)
        self.rutas_activas[id_dron] = {"waypoints": [(lat, lon)], "ruta": linea_vuelo}
        self.historial_visitados[id_dron] = [(inicio_lat, inicio_lon)]

        self.log_telemetria(f"[{id_dron}] Despegue autorizado hacia vector asignado ({self.conteo_uav}/3).")

    def desplegar_mini_ambulancia_click(self, coords):
        if self.conteo_mini >= 3:
            self.log_telemetria("[ALERTA] Capacidad máxima alcanzada: 3 Mini-Ambulancias activas.")
            return

        self.conteo_mini += 1
        id_mini = f"MINI-{self.conteo_mini}"
        lat, lon = coords
        # Sigue los waypoints trazados antes de llegar al objetivo
        puntos = list(self.waypoints_temporales) + [(lat, lon)]
        self.iniciar_movimiento_vehiculo(id_mini, puntos, COLOR_MINI)
        self.log_telemetria(f"[{id_mini}] Despacho confirmado hacia objetivo ({self.conteo_mini}/3).")

    def desplegar_ambulancia_click(self, coords):
        if self.conteo_amb >= 3:
            self.log_telemetria("[ALERTA] Capacidad máxima alcanzada: 3 Ambulancias activas.")
            return

        self.conteo_amb += 1
        id_amb = f"AMB-{self.conteo_amb}"
        lat, lon = coords
        puntos = list(self.waypoints_temporales) + [(lat, lon)]
        self.iniciar_movimiento_vehiculo(id_amb, puntos, COLOR_ROVER)
        self.log_telemetria(f"[{id_amb}] Soporte médico pesado despachado ({self.conteo_amb}/3).")

    def iniciar_movimiento_vehiculo(self, id_unidad, puntos_pendientes, color_activo):
        inicio_lat = self.marcador_base.position[0] if self.marcador_base else LAT_INICIAL
        inicio_lon = self.marcador_base.position[1] if self.marcador_base else LON_INICIAL

        self.flota_activa[id_unidad] = self.mapa.set_marker(
            inicio_lat, inicio_lon, text=id_unidad, 
            marker_color_circle="black", marker_color_outside=color_activo, 
            command=self.abrir_feed_video
        )
        ruta_completa = [(inicio_lat, inicio_lon)] + puntos_pendientes
        ruta_visual = self.mapa.set_path(ruta_completa, color="#58a6ff", width=2)
        self.rutas_activas[id_unidad] = {"waypoints": puntos_pendientes, "ruta": ruta_visual}
        self.historial_visitados[id_unidad] = [(inicio_lat, inicio_lon)]

    def retorno_a_base(self):
        if not self.marcador_base:
            self.log_telemetria("[ALERTA] No hay BASE fijada para ordenar el retorno.")
            return

        for id_unidad, marcador in self.flota_activa.items():
            lat_actual, lon_actual = marcador.position
            if id_unidad in self.rutas_activas and self.rutas_activas[id_unidad]["ruta"]:
                self.rutas_activas[id_unidad]["ruta"].delete()

            if "UAV" in id_unidad:
                camino_regreso = [self.marcador_base.position]
                ruta_visual = self.mapa.set_path([(lat_actual, lon_actual), self.marcador_base.position], color=COLOR_DRON, width=2)
            else:
                camino_regreso = self.historial_visitados.get(id_unidad, [self.marcador_base.position])[::-1]
                ruta_visual = self.mapa.set_path([(lat_actual, lon_actual)] + camino_regreso, color="#e3b341", width=2)

            self.rutas_activas[id_unidad] = {"waypoints": camino_regreso, "ruta": ruta_visual}

        self.log_telemetria("[COMANDO] PROTOCOLO RTB: Todo el enjambre replegándose a base.")

    def toggle_pausa(self):
        if getattr(self, 'sistema_pausado', False):
            self.sistema_pausado = False
            self.btn_stop.config(text="🛑 ALTO TOTAL", bg="#da3633")
            self.log_telemetria("[SISTEMA] Marcha reanudada.")
        else:
            self.sistema_pausado = True
            self.btn_stop.config(text="▶ CONTINUAR MARCHA", bg="#238636")
            self.log_telemetria("[EMERGENCIA] ALTO TOTAL ORDENADO.")

    def abrir_feed_video(self, marcador):
        visor = tk.Toplevel(self.master)
        visor.title(f"V-AGT | Sensor Óptico Táctico - {marcador.text}")
        visor.geometry("660x540")
        visor.configure(bg="#0B0E14")
        
        lbl_video = tk.Label(visor, bg="#0B0E14", text="Sincronizando enlace de video...", fg="#8b949e", font=("Consolas", 10))
        lbl_video.pack(expand=True, fill=tk.BOTH)

        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        
        if "UAV" in marcador.text:
            nombre_archivo = "video_dron.mp4"
            canal_tag = f"EO/IR AIR RECON [{marcador.text}]"
        elif "MINI" in marcador.text:
            nombre_archivo = "video_mini_ambulancia.mp4"
            canal_tag = f"SCOUT MICRO-CAM [{marcador.text}]"
        else:
            nombre_archivo = "video_ambulancia.mp4"
            canal_tag = f"HEAVY RESCUE CAM [{marcador.text}]"
            
        ruta_video = os.path.join(directorio_actual, nombre_archivo)

        def ciclo_video():
            cap = cv2.VideoCapture(ruta_video)
            if not cap.isOpened():
                lbl_video.configure(text=f"[!] No se pudo abrir {nombre_archivo}\nVerifica que el archivo exista en la carpeta.", fg="#da3633")
                return

            while visor.winfo_exists():
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                frame = cv2.resize(frame, (640, 480))
                hora_str = time.strftime("%H:%M:%S")
                cv2.putText(frame, f"REC [LIVE] | {canal_tag}", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
                cv2.putText(frame, f"TIME: {hora_str} | LINK: SECURE", (15, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

                cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img_pil = Image.fromarray(cv2image)

                def mostrar_frame(img=img_pil):
                    if visor.winfo_exists():
                        imgtk = ImageTk.PhotoImage(image=img)
                        lbl_video.imgtk = imgtk
                        lbl_video.configure(image=imgtk, text="")

                visor.after(0, mostrar_frame)
                time.sleep(0.033)
                
            cap.release()

        threading.Thread(target=ciclo_video, daemon=True).start()

        def desactivar_unidad():
            for id_unidad, datos_ruta in list(self.rutas_activas.items()):
                if self.flota_activa.get(id_unidad) == marcador:
                    if datos_ruta["ruta"]:
                        datos_ruta["ruta"].delete()
                    del self.rutas_activas[id_unidad]

            if "UAV" in marcador.text and self.conteo_uav > 0:
                self.conteo_uav -= 1
            elif "MINI" in marcador.text and self.conteo_mini > 0:
                self.conteo_mini -= 1
            elif "AMB" in marcador.text and self.conteo_amb > 0:
                self.conteo_amb -= 1

            marcador.delete()
            visor.destroy()
            self.log_telemetria(f"[SISTEMA] Activo {marcador.text} desmovilizado.")

        btn_eliminar = tk.Button(
            visor, text="Desmovilizar Unidad / Cerrar Feed", 
            bg="#da3633", fg="white", bd=0, font=("Arial", 9, "bold"), 
            command=desactivar_unidad
        )
        btn_eliminar.pack(side=tk.BOTTOM, fill=tk.X, ipady=6)

    def buscar_ubicacion(self):
        busqueda = self.entrada_busqueda.get()
        if busqueda and busqueda != "Lat,Lon o Ciudad...":
            try:
                if "," in busqueda:
                    lat, lon = map(float, busqueda.split(","))
                    self.mapa.set_position(lat, lon)
                else:
                    self.mapa.set_address(busqueda)
            except Exception:
                self.log_telemetria("[ERROR] Búsqueda no válida.")

    def centrar_en_base(self):
        if self.marcador_base:
            lat, lon = self.marcador_base.position
            self.mapa.set_position(lat, lon)

    def log_telemetria(self, mensaje):
        hora = time.strftime("%H:%M:%S")
        self.consola.insert(tk.END, f"[{hora}] {mensaje}\n")
        self.consola.see(tk.END)

    # --------------------------------------------------------------------------
    # PARTE 6: MOTOR DE NAVEGACIÓN Y CINEMÁTICA
    # --------------------------------------------------------------------------
    def motor_navegacion(self):
        if getattr(self, 'sistema_pausado', False):
            self.master.after(2000, self.motor_navegacion)
            return

        for id_unidad in list(getattr(self, 'rutas_activas', {}).keys()):
            if id_unidad in self.flota_activa and self.rutas_activas[id_unidad]["waypoints"]:
                marcador = self.flota_activa[id_unidad]
                lat_actual, lon_actual = marcador.position
                obj_lat, obj_lon = self.rutas_activas[id_unidad]["waypoints"][0] 
                
                dist_lat = obj_lat - lat_actual
                dist_lon = obj_lon - lon_actual
                dist_total = (dist_lat**2 + dist_lon**2)**0.5
                
                # Velocidades calibradas según naturaleza del activo
                if "UAV" in id_unidad:
                    velocidad = 0.00030   # Dron rápido
                elif "MINI" in id_unidad:
                    velocidad = 0.00022   # Mini-ambulancia ligera
                else:
                    velocidad = 0.00014   # Ambulancia pesada
                
                if dist_total <= velocidad:
                    marcador.set_position(obj_lat, obj_lon)
                    if id_unidad not in getattr(self, 'historial_visitados', {}):
                        self.historial_visitados[id_unidad] = []
                    self.historial_visitados[id_unidad].append((obj_lat, obj_lon))
                    self.rutas_activas[id_unidad]["waypoints"].pop(0) 
                    
                    if not self.rutas_activas[id_unidad]["waypoints"]: 
                        self.log_telemetria(f"[INFO] {id_unidad} arribó a estación de misión.")
                        
                        # --- NUEVO: Avisar al cerebro que la MINI llegó para encender la cámara ---
                        if "MINI" in id_unidad:
                            def avisar_llegada():
                                try:
                                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                                        s.settimeout(1.0)
                                        s.connect(('127.0.0.1', 65432))
                                        s.sendall("C2|{}|MINI_EN_POSICION".encode('utf-8'))
                                except:
                                    pass
                            threading.Thread(target=avisar_llegada, daemon=True).start()
                        # -------------------------------------------------------------------------
                    else:
                        self.log_telemetria(f"[INFO] {id_unidad} superó waypoint de tránsito.")
                        
                else:
                    nueva_lat = lat_actual + (dist_lat / dist_total) * velocidad
                    nueva_lon = lon_actual + (dist_lon / dist_total) * velocidad
                    marcador.set_position(nueva_lat, nueva_lon)

        self.master.after(2000, self.motor_navegacion)

# ------------------------------------------------------------------------------
# PARTE 7: PUNTO DE ENTRADA DEL SISTEMA
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = AgenteNavegacion(root)
    root.mainloop()