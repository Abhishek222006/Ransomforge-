# 🛡️ RansomForge — ThreatLens

> Lightweight real-time ransomware and threat detection platform for SMEs.

RansomForge (ThreatLens) is a cybersecurity project focused on helping small and medium-sized businesses identify suspicious endpoint activity through process monitoring, detection rules, threat scoring, and a simple security dashboard.

## 🚨 Problem

Small and medium-sized businesses often lack access to affordable, easy-to-use endpoint security tools. Ransomware and suspicious processes can cause serious damage before they are detected.

RansomForge aims to provide lightweight security visibility by monitoring system activity and highlighting potentially risky behavior.

## 💡 Solution

The platform follows a simple defensive security workflow:

**Monitor → Detect → Score → Alert → Visualize**

It is designed to:

- 🔍 Monitor running processes
- 📊 Track system resource usage
- ⚠️ Identify suspicious behavior using detection rules
- 🎯 Assign threat scores to suspicious activity
- 🚨 Surface security alerts
- 🖥️ Present security information through a web dashboard

## 🏗️ Architecture

```text
Endpoint Activity
       │
       ▼
Runtime Monitoring
       │
       ▼
Detection Engine
 ┌─────┼─────────────┐
 │     │             │
Rules  Behavior   Threat Scoring
 └─────┼─────────────┘
       │
       ▼
Alerts / Outputs
       │
       ▼
ThreatLens Dashboard
```

## 📁 Project Structure

```text
RansomForge_Hacknovate-main/
│
├── backend/
│   └── detection/
│
├── frontend/
│   ├── src/
│   └── public/
│
├── runtime_watch/
├── scripts/
├── datasets/
├── outputs/
│
├── PROJECT_CONTEXT.md
├── PROJECT_STRUCTURE.md
├── README.md
└── .gitignore
```

## ⚙️ Technology Stack

### Frontend
- React
- Vite
- JavaScript
- HTML / CSS

### Backend
- Python
- Process monitoring
- Detection rules
- Threat scoring

### Development
- Git
- GitHub
- VS Code

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Abhishek222006/Ransomforge-.git
cd Ransomforge-
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. Backend

Create a Python virtual environment:

```bash
python -m venv venv
```

On Windows:

```bash
venv\Scripts\activate
```

Install backend dependencies if a `requirements.txt` file is present:

```bash
pip install -r requirements.txt
```

> Run the backend entry point specified by the project files/configuration.

## 🧪 Detection Workflow

```text
System Activity
      ↓
Process Monitoring
      ↓
Behavior / Signal Collection
      ↓
Detection Rules
      ↓
Threat Scoring
      ↓
Risk Classification
      ↓
Security Alert
      ↓
Dashboard
```

## 🎯 Risk Classification

| Level | Meaning |
|---|---|
| 🟢 Low | Normal or expected activity |
| 🟡 Medium | Activity requiring attention |
| 🟠 High | Strongly suspicious activity |
| 🔴 Critical | Activity requiring immediate investigation |

## 🔐 Security Focus

RansomForge is intended as a **defensive cybersecurity and endpoint monitoring project**.

Potential security signals include:

- Unusual process behavior
- Abnormal resource consumption
- Suspicious process activity
- Rule-based threat indicators
- Changes in system behavior

## 🔮 Future Improvements

- Machine-learning based behavioral detection
- File-system activity monitoring
- Network activity analysis
- Automated incident response
- Process isolation
- Historical security analytics
- Improved threat visualization
- Email / notification alerts
- Multi-endpoint monitoring
- Advanced threat classification

## 🏆 Hacknovate

RansomForge was developed for **Hacknovate**, with the goal of creating an accessible and lightweight endpoint threat detection solution for SMEs.

### Vision

> Make meaningful endpoint security visibility more accessible without the complexity and cost of enterprise security infrastructure.

## ⚠️ Disclaimer

RansomForge is a defensive cybersecurity research project intended for authorized systems and testing environments.

Do not deploy monitoring or security components on systems without appropriate authorization.

## 👨‍💻 Contributors

**Abhishek222006**

Built for Hacknovate. 🚀

## 📄 License

This project is licensed under the **MIT License**.

See [`LICENSE`](LICENSE) for details.
