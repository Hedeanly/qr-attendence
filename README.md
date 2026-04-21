# QR Attendance System

A secure QR-based attendance tracking system with anti-cheat, role-based access control, and real-time dashboard. Built with FastAPI, React, and PostgreSQL — containerized with Docker and orchestrated with Kubernetes.

---

## Architecture

```
                        ┌─────────────────────────────────────┐
                        │         Kubernetes Cluster           │
                        │         (namespace: qr-attendance)   │
                        │                                      │
  Browser               │  ┌─────────────┐                    │
     │                  │  │   Ingress   │  nginx-ingress      │
     │ HTTP             │  │  Controller │                    │
     └─────────────────►│  └──────┬──────┘                    │
                        │         │                            │
                        │    /    │    /api/*                  │
                        │         │                            │
                        │  ┌──────▼──────┐  ┌──────────────┐  │
                        │  │  Frontend   │  │   Backend    │  │
                        │  │  (nginx)    │  │  (FastAPI)   │  │
                        │  │  2 replicas │  │  3 replicas  │  │
                        │  └─────────────┘  └──────┬───────┘  │
                        │                          │           │
                        │                  ┌───────▼───────┐  │
                        │                  │   PostgreSQL  │  │
                        │                  │  StatefulSet  │  │
                        │                  │   + 1Gi PVC   │  │
                        │                  └───────────────┘  │
                        │                                      │
                        │  HPA: backend scales 2→10 pods       │
                        │       when CPU > 60%                 │
                        └─────────────────────────────────────┘
```

### Why Kubernetes?

When a lecturer starts a class session and 100+ students simultaneously scan the QR code, the API receives a burst of requests in seconds. Kubernetes handles this with a **HorizontalPodAutoscaler** that automatically scales the stateless FastAPI backend from 2 to 10 pods under load — then scales back down when idle.

PostgreSQL runs as a **StatefulSet** (not a Deployment) because it is stateful — it needs a stable identity and persistent storage across restarts. The frontend is stateless and runs as a regular **Deployment**.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy, PostgreSQL |
| Frontend | React, Vite, Axios |
| Auth | JWT (python-jose), bcrypt |
| QR | qrcode, html5-qrcode |
| Storage | Cloudinary |
| Containerization | Docker (multi-stage builds) |
| Orchestration | Kubernetes (minikube for local) |
| Reverse Proxy | nginx |

---

## Features

- QR code generation per session with auto-refresh (anti-cheat)
- Role-based access: Admin, Lecturer, Student
- Manual attendance override
- At-risk student detection
- Real-time attendance dashboard
- Learning resource management per class

---

## Running Locally with Docker

**Prerequisites:** Docker Desktop

```bash
# 1. Clone the repo
git clone <repo-url>
cd qr-attendance

# 2. Set up environment
copy .env.example .env   # Windows
# cp .env.example .env   # Mac/Linux

# 3. Start all services
docker compose up --build
```

| URL | Service |
|---|---|
| `http://localhost` | React frontend |
| `http://localhost:8000` | FastAPI backend |
| `http://localhost:8000/docs` | Interactive API docs |

To stop: `Ctrl+C`, then `docker compose down`

---

## Deploying with Kubernetes

**Prerequisites:** Docker Desktop, minikube, kubectl

```bash
# 1. Start minikube
minikube start --driver=docker

# 2. Enable ingress controller
minikube addons enable ingress

# 3. Load local images into minikube
minikube image load qr-attendance-backend:latest
minikube image load qr-attendance-frontend:latest

# 4. Apply all manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/postgres/
kubectl apply -f k8s/backend/
kubectl apply -f k8s/frontend/
kubectl apply -f k8s/ingress.yaml

# 5. Check everything is running
kubectl get all -n qr-attendance

# 6. Access the app
kubectl port-forward -n qr-attendance service/frontend 3000:80
kubectl port-forward -n qr-attendance service/backend 8000:8000
```

| URL | Service |
|---|---|
| `http://localhost:3000` | React frontend |
| `http://localhost:8000/docs` | API docs |

---

## Kubernetes Manifests

```
k8s/
  namespace.yaml          — isolated environment for all resources
  configmap.yaml          — non-sensitive config (db name, usernames)
  secret.yaml             — sensitive values (passwords, keys) base64 encoded
  postgres/
    pvc.yaml              — 1Gi persistent volume for database data
    statefulset.yaml      — PostgreSQL with liveness & readiness probes
    service.yaml          — ClusterIP (internal only)
  backend/
    deployment.yaml       — 3 replicas, resource limits, health probes
    service.yaml          — ClusterIP (internal only)
    hpa.yaml              — autoscale 2→10 pods when CPU > 60%
  frontend/
    deployment.yaml       — 2 replicas, health probes
    service.yaml          — ClusterIP (internal only)
  ingress.yaml            — routes /api/* → backend, / → frontend
```

---

## Default Credentials

| Role | Username | Password |
|---|---|---|
| Admin | admin | admin123 |

> Change these in `.env` before any real deployment.
