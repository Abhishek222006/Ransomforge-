# RansomForge: Project Structure & Architecture

A professional overview of the RansomForge SOC Platform, designed for real-time ransomware monitoring, threat detection, and incident response.

---

## 1. Project Directory Tree

```text
RansomForge_Hacknovate/
├── backend/                    # FastAPI Backend Application
│   ├── detection/              # ML/Rule-based detection engines
│   ├── monitors/               # System & File monitoring services
│   ├── routers/                # Modular API route definitions
│   │   ├── events.py           # Historical event retrieval
│   │   └── health.py           # System status endpoints
│   ├── services/               # Core business logic & utilities
│   │   ├── database.py         # SQLite Event Store (OO wrapper)
│   │   ├── db.py               # Functional database helpers
│   │   └── websocket_manager.py # Real-time client connection handler
│   ├── main.py                 # Application entry point & WS logic
│   ├── ransomforge.db          # Primary SQLite database
│   ├── ransomforge_events.db   # Specialized event storage
│   └── requirements.txt        # Python dependencies
├── datasets/                   # Training and testing datasets (ML)
│   ├── train/                  # Training data for threat detection
│   └── test/                   # Validation datasets
├── frontend/                   # React + Vite Frontend Application
│   ├── src/
│   │   ├── assets/             # Static assets (images, icons)
│   │   ├── components/         # Reusable UI components
│   │   │   ├── Dashboard/      # Main monitoring widgets
│   │   │   └── Layout/         # Sidebar, Navbar, etc.
│   │   ├── pages/              # Page-level components (Alerts, Assets)
│   │   ├── services/           # Communication layer
│   │   │   ├── api.js          # REST API client
│   │   │   └── socket.js       # WebSocket client & reconnect logic
│   │   ├── App.jsx             # Root component & state management
│   │   ├── index.css           # Global styles & Tailwind imports
│   │   └── main.jsx            # React entry point
│   ├── package.json            # Node.js dependencies
│   └── vite.config.js          # Vite build configuration
├── outputs/                    # ML model artifacts and baseline results
├── runtime_watch/              # Monitored directory for file activity
├── scripts/                    # Utility and demo scripts
├── PROJECT_CONTEXT.md          # High-level project context
├── PROJECT_STRUCTURE.md        # [THIS FILE] Architecture documentation
└── README.md                   # Quickstart guide
```

---

## 2. Core Architecture

### Frontend Architecture (React/Vite)
- **Framework**: React 18+ powered by Vite for rapid development.
- **State Management**: Centralized reactive state in `App.jsx` handling WebSocket events, threat scores, and operation status.
- **Visuals**: 
  - **Framer Motion**: Powering smooth transitions, glassmorphism effects, and "breathing" UI elements.
  - **Tailwind CSS**: Utility-first styling for a premium dark-mode SOC aesthetic.
  - **Lucide React**: Modern, consistent iconography.
- **Networking**: Dual-layer communication using standard REST (`api.js`) for data fetching and WebSockets (`socket.js`) for real-time telemetry.

### Backend Architecture (FastAPI)
- **Framework**: FastAPI (Asynchronous Python) for high-concurrency WebSocket support.
- **Storage**: Persistent SQLite databases for event logging and system state.
- **Monitoring**: `FileMonitorService` uses low-level file system hooks to detect modifications in the `runtime_watch` directory.
- **Concurrency**: Background tasks handle simulated "demo" pulses and system-wide scans without blocking the main event loop.

---

## 3. Real-time Pipeline & WebSocket Flow

### Event Pipeline
1. **Detection**: `FileMonitorService` detects a file change or the `demo_loop` generates a pulse.
2. **Standardization**: Raw events are mapped to a structured security format (Type, Severity, Path, Score).
3. **Persistence**: The event is recorded in the SQLite store for audit trails.
4. **Broadcast**: `WebSocketManager` pushes the JSON payload to all connected frontend clients at the `/ws` endpoint.
5. **Ingestion**: Frontend `socket.js` receives the message and triggers a callback in `App.jsx`.
6. **Re-render**: React updates the `threatScore`, `events` feed, and `attackStage` timeline instantly.

### WebSocket Event Types
- `NEW_EVENT`: Triggered on file system activity or simulated alert.
- `THREAT_UPDATE`: Updates the global threat score and "Stage" meter.
- `ALERT`: High-severity notifications requiring toast displays.
- `SCAN_PROGRESS`: Real-time progress updates for the "Full Scan" operation.
- `NETWORK_ISOLATED`: Signal that the host containment protocol is active.

---

## 4. API Structure

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | GET | Basic health check/landing. |
| `/events/recent` | GET | Fetches historical security logs from SQLite. |
| `/processes/recent` | GET | Returns simulated process telemetry and risk levels. |
| `/assets/honeypots` | GET | Lists status of sensitive "canary" files. |
| `/operations/full-scan` | POST | Triggers a simulated deep-system scan. |
| `/operations/isolate-network` | POST | Activates global host isolation mode. |
| `/demo/event` | POST | Manually injects a high-severity ransomware event. |

---

## 5. Important Components & Modules

### Frontend
- **ThreatScoreCard**: Dynamic radial/gauge visualization of current risk.
- **AttackTimeline**: Visual mapping of the Ransomware Kill-chain (Delivery -> Encryption -> Exfiltration).
- **LiveEventFeed**: Auto-scrolling, severity-coded list of incoming telemetry.
- **ProcessAnomalyPanel**: Monitoring view for suspicious system processes.

### Backend
- **FileMonitorService**: The "eyes" of the application, watching disk activity.
- **WebSocketManager**: The "heart" of real-time communication.
- **SQLiteEventStore**: The "memory" ensuring data persists across restarts.

---

## 6. Cleanup & Development Suggestions

- **Database Consolidation**: Currently, two separate DB helpers (`db.py` and `database.py`) and two DB files exist. These should be merged into a single robust service.
- **State Management**: As the dashboard grows, moving from `useState` in `App.jsx` to a `Context API` or `Zustand` store would improve component separation.
- **Demo Toggle**: The `_realtime_demo_loop` should be toggleable via environment variables for production vs. demo modes.
- **Path Handling**: Standardize cross-platform path handling for the `runtime_watch` directory (currently hardcoded to relative paths).

---

## 7. Demo Flow Architecture

1. **Pulse**: Backend starts a background timer that emits "normal" activity every 4 seconds to keep the UI alive.
2. **Trigger**: User clicks "Simulate Attack" or modifies a file in `runtime_watch`.
3. **Escalation**: Threat score jumps from green/yellow to critical red. The `AttackTimeline` advances to the "Encryption" stage.
4. **Intervention**: User clicks "Isolate Network." The UI transitions into a "High Danger" state with red banners and glowing effects.
5. **Resolution**: User runs "Full Scan" to verify containment and identify infected assets.
