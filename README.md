# KirkinX | Autonomous Rescue Swarm C2

A distributed Command and Control (C2) and swarm robotics platform designed for humanitarian search and rescue (SAR) operations in disaster environments. The system combines centralized tactical reasoning powered by Meta AI models (Meta Muse Wonder / Llama 3) with real-time edge computer vision (YOLOv8) optimized for resource-constrained field hardware.

---

## 📋 Hackathon Scope: Pre-existing Work vs. Built During the Hackathon

In strict adherence to hackathon transparency guidelines, the boundary of development is detailed below:

* **Pre-existing Base:**
  * Fundamental Tkinter visual skeleton.
  * Basic offline satellite tile caching structure utilizing `tkintermapview`.

* **Developed 100% from Scratch During the Hackathon:**
  1. **Central Tactical Agent (`T-AGT.py`):** Complete C2 server architecture, structured system prompts for situational reasoning, Meta Model API integration (Muse Wonder / Llama 3), and autonomous JSON-schema directive generation.
  2. **Visual Sensor Core (`V-AGT_procesador.py`):** Real-time YOLOv8 edge inference pipeline, automated network standby/polling mechanism, optical stream optimization (640x480), and low-latency socket dispatching under strict hardware limits (emulated on an Intel Core i3 / 8GB RAM host without discrete GPU).
  3. **Distributed Communication Protocol:** Custom low-latency TCP socket architecture (Port 65432) and asynchronous 1 Hz telemetry synchronization across independent processes.
  4. **Closed Autonomous Loop (Zero-Touch Loop):** End-to-end autonomous inter-agent choreography (scout waypoint arrival $\rightarrow$ automated camera wake-up $\rightarrow$ computer vision casualty confirmation $\rightarrow$ automated tactical deployment of heavy medical UGV without human intervention).

---

## 📌 Project Overview

In natural disasters (earthquakes, structural collapses, or inaccessible mountainous terrain), rapid response is critical. KirkinX coordinates Unmanned Ground Vehicles (UGVs) through a hybrid edge-cloud cognitive architecture:

* **Central Cognitive Reasoning:** A Meta model evaluates mission telemetry, operational state, and field priorities to orchestrate rescue logistics autonomously.
* **Lightweight Edge Perception:** YOLOv8 runs real-time visual inference directly on local hardware, emulating the size, weight, and power (SWaP) constraints of field micro-robots.

---

## 🛰️ Distributed Multi-Agent Architecture

The platform decouples navigation, perception, and decision-making into three standalone processes communicating over local TCP sockets (Port 65432):

1. **`T-AGT.py` (Tactical Rescue Agent - Meta AI Core):**
   * Central mission C2 decision engine.
   * Processes fleet telemetry and optical emergency payloads.
   * Leverages Meta Muse Wonder / Llama 3 to generate structured JSON execution directives without human oversight.

2. **`N-AGT.py` (Navigation & Blue Force Tracking Agent):**
   * Tactical GUI developed with Tkinter and `tkintermapview`.
   * Manages 1 Hz telemetry monitoring, dynamic waypoint plotting, and kinematic path traversal.
   * Mathematically detects waypoint arrival and broadcasts arrival triggers across the network.

3. **`V-AGT_procesador.py` (Visual Sensor Core - YOLOv8 Edge AI):**
   * Optimized real-time computer vision engine.
   * Remains in low-power standby via silent polling until the scout UGV arrives on target.
   * Identifies casualties, validates confidence thresholds, and transmits immediate alerts (`CASUALTY_LOCATED`) to the C2 server.

---

## ⚡ Autonomous Operational Flow (Zero-Touch Loop)

```text
[ Operator Command ]
         │
         ▼
[ N-AGT: Scout UGV Deployed ] ──(Reaches Target)──► [ Socket Alert: MINI_EN_POSICION ]
                                                              │
                                                              ▼
[ V-AGT: Optical Feed Activated ] ◄──(POLL_VIDEO)── [ T-AGT: Server Synchronized ]
         │
         ▼
[ YOLOv8: Casualty Detected ] ──(Alert: CASUALTY_LOCATED)──► [ T-AGT: Meta Reasoning ]
                                                                      │
                                                                      ▼
[ N-AGT: Heavy Ambulance Deployed ] ◄──(POLL_ALERTA: Auto-Dispatch)───┘
```

1. **Initial Deployment:** Operator directs the light scout unit (`MINI-1`) toward the target area via natural language.
2. **Telemetry Synchronization:** Upon reaching destination coordinates, `N-AGT` fires a socket notification (`MINI_EN_POSICION`) to `T-AGT`.
3. **Automated Vision Wake-Up:** `V-AGT` polls the network (`POLL_VIDEO`), detects scout arrival, and automatically activates the camera feed.
4. **Edge Identification:** YOLOv8 verifies the victim on the ground, exceeds the confidence threshold, and transmits an emergency signal to the C2 core.
5. **Tactical Assessment:** `T-AGT` processes the event with the Meta model and issues an autonomous medical deployment directive.
6. **Autonomous Rescue:** `N-AGT` intercepts the directive via background polling and instantly dispatches the heavy medical ambulance (`AMB-1`) to the victim's verified coordinates without manual operator intervention.

---

## 🛠️ Installation & Requirements

Ensure Python 3.10+ is installed along with the required dependencies:

```bash
pip install ultralytics opencv-python tkintermapview requests
```

## 🚀 Execution Guide

Run each agent in a separate terminal window in the following order:

```bash
# Terminal 1: Tactical Server (Meta Muse Wonder / Llama 3 C2 Engine)
python3 T-AGT.py

# Terminal 2: Edge Vision Sensor (YOLOv8 Optical Core)
python3 V-AGT_procesador.py

# Terminal 3: Navigation Interface (C2 Map & Telemetry GUI)
python3 N-AGT.py
```
