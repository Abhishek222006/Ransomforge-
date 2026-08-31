# RansomForge Hackathon Context

## Project

RansomForge is a realtime ransomware detection and cybersecurity monitoring dashboard built for a hackathon.

Goal:
Detect suspicious ransomware-like activity and display realtime alerts through a SOC-style dashboard.

---

# Team

2 developers.

## Roles

Frontend:

* React dashboard
* realtime UI
* websocket integration
* dashboard UX

Backend:

* FastAPI
* websocket broadcasting
* detection engine
* monitoring scripts

---

# Current Tech Stack

## Frontend

* React (Vite)
* JavaScript
* Tailwind CSS
* lucide-react
* framer-motion
* recharts
* Native WebSocket

## Backend

* FastAPI
* Python
* watchdog
* psutil
* SQLite

---

# Current Frontend Status

Completed:

* Tailwind setup fixed
* SOC dashboard UI completed
* Sidebar/navbar completed
* Threat score card completed
* Live event feed completed
* Alert summary completed
* WebSocket frontend integration completed
* Connection status indicator completed
* Realtime UI stability improvements completed

Frontend websocket listens for:

* NEW_EVENT
* THREAT_UPDATE

---

# Current Backend Status

In progress:

* FastAPI websocket endpoint
* realtime event broadcaster
* dummy threat events
* SQLite logging

Next goals:

* watchdog file monitoring
* process monitoring
* threat scoring
* ransomware simulation

---

# Current Realtime Architecture

backend threat event
↓
websocket broadcast
↓
frontend receives event
↓
dashboard updates live

---

# Important Project Rules

* Keep architecture simple
* No overengineering
* Hackathon-first approach
* Functionality > perfection
* Realtime demo is highest priority
* Avoid unnecessary libraries

---

# Important Frontend Rules

* Do not over-polish UI
* Keep dashboard stable
* Use realtime-friendly layout
* Maintain dummy fallback events
* Prevent layout shifts during streaming

---

# Important Backend Rules

* No Redis
* No socket.io
* Native FastAPI websocket only
* Keep detection engine modular
* SQLite only for hackathon

---

# Current Folder Structure

frontend/
backend/
scripts/
outputs/

Frontend important folders:
src/components/
src/services/socket.js

---

# Next Major Milestone

Backend sends realtime threat events successfully to frontend dashboard.

Success flow:

simulate threat
↓
backend event
↓
websocket broadcast
↓
frontend live update

---

# Demo Vision

User clicks:
"Simulate Attack"

Then:

* threat score spikes
* live feed updates
* critical alert appears
* ransomware activity visualized
* optional isolation action triggered

---

# Current Git Workflow

Before coding:
git pull origin main

After work:
git add .
git commit -m "message"
git push origin main
