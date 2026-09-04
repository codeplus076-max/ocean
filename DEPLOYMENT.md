# PELAGOS Production Deployment Guide
## Deploying Backend on Render & Frontend on Vercel

This guide walks you step-by-step through deploying the **FastAPI Backend on Render** and the **Interactive 3D Visualizer on Vercel**.

---

### Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│               FRONTEND (Vercel)                        │
│  - Hosted on: https://your-project.vercel.app          │
│  - Tech: React, Cesium, Three.js, Tailwind             │
│  - Static files in: ./frontend                         │
└──────────────────────────┬─────────────────────────────┘
                           │ HTTPS / WSS
                           ▼
┌────────────────────────────────────────────────────────┐
│               BACKEND (Render)                         │
│  - Hosted on: https://your-service.onrender.com        │
│  - Tech: FastAPI, Uvicorn, Xarray, Copernicus, Argo    │
│  - Files: main.py, config.py, app/                     │
└────────────────────────────────────────────────────────┘
```

---

### Prerequisites

1. A [GitHub](https://github.com/) account
2. A [Render](https://render.com/) account (free tier available)
3. A [Vercel](https://vercel.com/) account (free Hobby tier available)

---

### Step 1: Push the Project to GitHub

Open PowerShell or Terminal in the project root (`ocean`):

```powershell
# 1. Initialize git (if not already initialized)
git init

# 2. Verify .gitignore is active (ensures .env and venv are ignored)
git status

# 3. Stage and commit all files
git add .
git commit -m "feat: production ready for Render backend and Vercel frontend"

# 4. Push to your GitHub repository
# (Create a new repository on github.com/new first)
git branch -M main
git remote add origin https://github.com/<YOUR-USERNAME>/<YOUR-REPO-NAME>.git
git push -u origin main
```

---

### Step 2: Deploy Backend to Render

You can deploy the backend using either **Method A (Automatic Blueprint)** or **Method B (Manual Setup)**.

#### Method A: Blueprint (Recommended - 1 Click)
1. Go to [dashboard.render.com](https://dashboard.render.com/).
2. Click **New +** → **Blueprint**.
3. Select your connected GitHub repository.
4. Render will detect `render.yaml` automatically.
5. In the environment variables section, enter your Copernicus credentials if you have them:
   - `CMEMS_USERNAME`
   - `CMEMS_PASSWORD`
   *(If left empty, the server automatically operates with demo & fallback data seamlessly without crashing).*
6. Click **Apply**. Render will build and deploy your service.

#### Method B: Manual Web Service Setup
1. In the Render Dashboard, click **New +** → **Web Service**.
2. Connect your GitHub repository.
3. Configure the settings:
   - **Name**: `pelagos-backend` (or your choice)
   - **Region**: Closest to your users (e.g., Oregon, Frankfurt, Singapore)
   - **Branch**: `main`
   - **Root Directory**: leave blank (root of repo)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
4. Expand **Advanced** → **Environment Variables**:
   - `PYTHON_VERSION`: `3.11.9`
   - `ARGO_BACKEND`: `erddap`
   - `DEFAULT_STRIDE`: `2`
   - `REFRESH_HOURS`: `6`
   - `ALLOWED_ORIGINS`: `*` (or your specific Vercel URL once deployed)
   - `CMEMS_USERNAME`: *(optional Copernicus email)*
   - `CMEMS_PASSWORD`: *(optional Copernicus password)*
5. Click **Create Web Service**.

#### Verify Backend
Once deployed, Render gives you a public URL (e.g. `https://pelagos-backend.onrender.com`).
Test it in your browser:
- Health Check: `https://pelagos-backend.onrender.com/health` (should return `{"status":"ok"}`)
- API Docs: `https://pelagos-backend.onrender.com/docs`
- API Metadata: `https://pelagos-backend.onrender.com/api/meta`

---

### Step 3: Deploy Frontend to Vercel

1. Log into [vercel.com](https://vercel.com/) and go to **Add New...** → **Project**.
2. Import your GitHub repository.
3. In the project configuration screen:
   - **Project Name**: `pelagos-ocean-3d` (or your choice)
   - **Framework Preset**: `Other`
   - **Root Directory**: Click **Edit** and select `frontend` *(very important!)*
   - Leave Build and Output settings as default.
4. Click **Deploy**.
5. Within 30-60 seconds, Vercel will provide your live URL (e.g. `https://pelagos-ocean-3d.vercel.app`).

---

### Step 4: Connect Frontend to Backend

Now tell your Vercel frontend where your Render backend lives.

#### Option 1: Edit `frontend/config.js` (Permanent)
In `frontend/config.js`, update the URL to your Render service:

```javascript
window.__PELAGOS_CONFIG__ = {
  API_BASE: "https://pelagos-backend.onrender.com/api"
};
```

Commit and push to GitHub:
```powershell
git add frontend/config.js
git commit -m "chore: point frontend config to live Render backend"
git push
```
Vercel will auto-deploy the change in seconds.

#### Option 2: Test Instantly via URL Parameter (No Redeploy Needed)
You can test your live Vercel frontend against your Render backend immediately by adding `?api=...`:
```
https://your-project.vercel.app/?api=https://pelagos-backend.onrender.com/api
```
The frontend automatically recognizes this query parameter and binds to your live backend!

---

### Summary of Key Files

| File | Purpose | Target |
| :--- | :--- | :--- |
| `frontend/index.html` | Interactive 3D Ocean Visualizer (Cesium + Three.js) | Vercel |
| `frontend/config.js` | Runtime config pointing to Render API | Vercel |
| `frontend/vercel.json` | Vercel routing rules & security headers | Vercel |
| `main.py` | FastAPI application entry point | Render |
| `config.py` | Centralized environment & layer configuration | Render |
| `render.yaml` | Infrastructure as Code Blueprint for Render | Render |
| `Dockerfile` | Optional container deployment specification | Render |
| `requirements.txt` | Complete backend Python dependencies | Render |
| `.gitignore` | Prevents secrets & virtual environments from being committed | Git |
