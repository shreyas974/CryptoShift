# Deploying CryptoShift to Vercel

CryptoShift is fully prepared for deployment on **Vercel**. You can deploy it using either:
1. **Option 1: All-in-One Full-Stack on Vercel (Fastest & Simplest)** — Both the React sunlit glass UI and the Node.js API run serverlessly on Vercel.
2. **Option 2: Hybrid Enterprise Deployment (Best for Production Banking)** — Deploy the React frontend to Vercel's global Edge CDN, while running the Python/Node backend on a persistent container platform (e.g. Railway, Render, or AWS ECS) where native Python test vectors run continuously.

---

## Architecture on Vercel

- **Frontend:** React 18 + Vite + TypeScript (built to `frontend/dist/` and served via Vercel Edge Network).
- **Backend API:** Node.js Serverless Function (`api/index.js`), mapped via `vercel.json` rewrites (`/api/*` → `/api/index.js`).
- **State & Storage:** Uses an ephemeral `/tmp/cryptoshift-data` directory seeded from `backend/data/state.json` on cold start, preventing read-only filesystem errors.
- **AI Engine:** Sarvam AI (`sarvam-105b-conversations`) executes via direct HTTPS calls using `SARVAM_API_KEY` configured in Vercel environment variables.

---

## Option 1: Step-by-Step Vercel Deployment (All-in-One)

### Method A: Deploy via GitHub (Recommended)

1. **Push your code to GitHub:**
   ```bash
   git add .
   git commit -m "Configure CryptoShift for Vercel deployment"
   git push origin main
   ```

2. **Import Project in Vercel:**
   - Go to [vercel.com/new](https://vercel.com/new).
   - Select your GitHub repository.
   
3. **Configure Project Settings in Vercel Dashboard:**
   - **Root Directory:** Click "Edit" and set to `cryptoshift_app`.
   - **Framework Preset:** `Vite` (or `Other`).
   - **Build Command:** `npm run build`
   - **Output Directory:** `frontend/dist`
   - **Install Command:** `npm run setup` (or default `npm install`)

4. **Add Environment Variables:**
   Under **Environment Variables**, add:
   - `SARVAM_API_KEY` = `<your-sarvam-api-key>`

5. **Deploy:**
   Click **Deploy**. Vercel will build the React bundle and deploy the serverless API in under 2 minutes.

---

### Method B: Deploy via Vercel CLI

If you prefer deploying from your terminal:

1. **Install Vercel CLI (or run with npx):**
   ```powershell
   cd cryptoshift_app
   npx vercel
   ```

2. **Follow the interactive prompts:**
   - `Set up and deploy?` → `Y`
   - `Which scope?` → Select your account or team
   - `Link to existing project?` → `N`
   - `Project name?` → `cryptoshift`
   - `In which directory is your code located?` → `./`
   - `Want to modify settings?` → `N` (settings are auto-read from `vercel.json`)

3. **Set the Sarvam API Key:**
   ```powershell
   npx vercel env add SARVAM_API_KEY production
   ```
   Paste your API key when prompted.

4. **Deploy to Production:**
   ```powershell
   npx vercel --prod
   ```

---

## Option 2: Hybrid Enterprise Deployment (Vercel Frontend + Container Backend)

In strict production banking environments where real Python 3.12 subprocesses must execute unit test vectors (`compileall`, `unittest`, `tools/verify_patch.py`), the recommended architecture is:

1. **Deploy Backend to Railway / Render / Fly.io:**
   - Deploy `cryptoshift_app` with command: `node backend/src/server.js`.
   - Set environment variables:
     - `SARVAM_API_KEY`
     - `CRYPTOSHIFT_PYTHON=python3`
   - You will get a backend URL, e.g., `https://cryptoshift-api.up.railway.app`.

2. **Deploy Frontend to Vercel:**
   - In `cryptoshift_app/frontend`:
     - In `vercel.json` on Vercel:
       ```json
       {
         "rewrites": [
           {
             "source": "/api/:match*",
             "destination": "https://cryptoshift-api.up.railway.app/api/:match*"
           },
           {
             "source": "/(.*)",
             "destination": "/index.html"
           }
         ]
       }
       ```
   - This delivers lightning-fast frontend loading from Vercel's global CDN, while all verification tests execute on your dedicated backend container.

---

## Configuration Files Added

1. **`cryptoshift_app/vercel.json`:**
   ```json
   {
     "version": 2,
     "buildCommand": "npm run build",
     "outputDirectory": "frontend/dist",
     "rewrites": [
       { "source": "/api/(.*)", "destination": "/api/index.js" },
       { "source": "/(.*)", "destination": "/index.html" }
     ]
   }
   ```

2. **`cryptoshift_app/api/index.js`:**
   Serverless API adapter that handles all incoming `/api/*` routes.

3. **`backend/src/store.js` & `backend/src/server.js`:**
   Updated to automatically detect `process.env.VERCEL`, write ephemeral state to `/tmp/cryptoshift-data`, and export the request handler for Vercel Serverless Functions.

---

## Verifying the Deployment

Once deployed to Vercel, visit your deployment URL (e.g., `https://cryptoshift.vercel.app`):
1. Navigate to `/api/health` to confirm the serverless backend is live:
   ```json
   {
     "ok": true,
     "startedAt": "...",
     "proposer": "sarvam-105b-conversations (Sarvam AI Cloud LLM Connected)",
     "sarvamAvailable": true,
     "node": "v20.x"
   }
   ```
2. Open the homepage: verify the sunlit glass theme, NIST standards matrix, and 8-stage migration tracker.
3. Open **AI Patch Studio** (`/patches`): click **"Run Sarvam AI Assessment"** to test live cloud reasoning.
4. Open **Anatomy Studio** (`/anatomy`): explore all 4 figures.

