# Frontend - Process Controller Web UI

A fast, responsive web interface for the Local Process Controller, built with vanilla HTML5, CSS3, and JavaScript.

---

## 📁 Files
- **`index.html`**: Main UI dashboard layout and process list tables.
- **`style.css`**: Styling, typography, color badges, responsive split-grid.
- **`app.js`**: Core logic for process polling, filtering, auto-mode toggling, and termination actions.
- **`nginx.conf`**: Pre-configured Nginx reverse proxy routing static requests and forwarding `/api` calls.
- **`Dockerfile`**: Lightweight container image using `nginx:alpine`.

---

## 🚀 Deployment Options

### Option 1: Bundled with Backend (FastAPI)
The backend FastAPI application automatically serves the static assets in this folder when running locally or packaged as an executable. No extra setup required.

### Option 2: Standalone Static Hosting (Vercel, Netlify, Cloudflare Pages, S3)
You can deploy this directory to any static hosting provider.
If the backend is hosted on a separate URL/port, specify the backend endpoint by adding this script tag at the head of `index.html` or before `app.js`:
```html
<script>
    window.API_BASE_URL = "https://your-backend-api-domain.com";
</script>
```

### Option 3: Docker / Nginx
Build and run using Nginx:
```bash
docker build -t process-controller-frontend .
docker run -p 80:80 process-controller-frontend
```

---

## 🛠 Local Development
Run a quick local web server inside this directory:
```bash
# Python
python -m http.server 3000

# Node.js
npx serve .
```
Open `http://localhost:3000` in your browser.

