import cv2
import json
import socket
import time
from ultralytics import YOLO

MODEL_PATH = "yolov8n.pt"
VIDEO_PATH = "video_mini_ambulancia.mp4"
CONF_THRESHOLD = 0.15
TARGET_CLASSES = [0, 67]

T_AGT_HOST = '127.0.0.1'
T_AGT_PORT = 65432

def enviar_alerta_a_tagt():
    payload = {"event": "CASUALTY_LOCATED"}
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((T_AGT_HOST, T_AGT_PORT))
            s.sendall(json.dumps(payload).encode('utf-8'))
            print("\n[V-AGT] ALERTA ENVIADA A T-AGT\n")
    except ConnectionRefusedError:
        print("\n[V-AGT ERROR] No se pudo conectar a T-AGT.\n")

def esperar_llegada_mini():
    print("\n" + "="*60)
    print("🟢 SISTEMA VISUAL EN STANDBY (EDGE COMPUTING)")
    print("Esperando confirmación de telemetría: Llegada al objetivo...")
    print("="*60 + "\n")
    
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                s.connect((T_AGT_HOST, T_AGT_PORT))
                s.sendall("C2|{}|POLL_VIDEO".encode('utf-8'))
                
                respuesta = s.recv(1024).decode('utf-8')
                if "INICIAR_VIDEO" in respuesta:
                    print("\n[V-AGT] ¡VEHÍCULO EN POSICIÓN! Encendiendo feed óptico...")
                    break
        except Exception:
            pass # Si el cerebro no responde, sigue esperando en silencio
            
        time.sleep(1) # Pregunta cada 1 segundo

def main():
    print("[V-AGT] Cargando modelo de visión y conectando cámara. Por favor espera...")
    model = YOLO(MODEL_PATH)
    cap = cv2.VideoCapture(VIDEO_PATH)
    alerta_enviada = False

    # --- ESPERA AUTÓNOMA EN RED (Reemplaza al ENTER manual) ---
    esperar_llegada_mini()
    # ----------------------------------------------------------

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (640, 480))

        results = model.predict(frame, conf=CONF_THRESHOLD, verbose=False)[0]
        detected = False
        best_conf = 0.0
        target_box = None

        for box in results.boxes:
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            if cls_id in TARGET_CLASSES:
                detected = True
                if conf > best_conf:
                    best_conf = conf
                    target_box = box.xyxy[0].cpu().numpy()

        cv2.putText(frame, "V-AGT SENSOR CORE | OPTICAL FEED", (30, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)

        if detected and target_box is not None:
            x1, y1, x2, y2 = map(int, target_box)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(frame, f"CASUALTY DETECTED [CONF: {best_conf:.2f}]",
                        (x1, max(y1 - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2, cv2.LINE_AA)
            
            if not alerta_enviada:
                enviar_alerta_a_tagt()
                alerta_enviada = True
        else:
            cv2.putText(frame, "STATUS: SCANNING AREA...", (30, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1, cv2.LINE_AA)

        cv2.imshow("KirkinX V-AGT Feed", frame)

        if cv2.waitKey(30) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()