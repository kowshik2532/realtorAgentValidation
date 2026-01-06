# Render Deployment Guide

## Quick Deploy

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository: `kowshik2532/realtorAgentValidation`
4. Render will auto-detect `render.yaml` configuration
5. Click "Create Web Service"

## Configuration

The `render.yaml` file is already configured with:

- **Build Command:** `pip install -r requirements.txt && playwright install chromium && playwright install-deps chromium`
- **Start Command:** `python main.py`
- **Python Version:** 3.11.0
- **Environment:** Python

## Manual Configuration (if needed)

If not using `render.yaml`, set these in Render dashboard:

### Build & Deploy

- **Build Command:**
  ```bash
  pip install -r requirements.txt && playwright install chromium && playwright install-deps chromium
  ```

- **Start Command:**
  ```bash
  python main.py
  ```

### Environment Variables

Render automatically sets:
- `PORT` - Server port (required)
- `HOST` - Server host (defaults to 0.0.0.0)

No additional environment variables needed.

## Important Notes

1. **Playwright Browsers:** The build command installs Chromium browser which is required for scraping
2. **Build Time:** First deployment may take 5-10 minutes due to Playwright browser installation
3. **Memory:** Ensure your Render plan has at least 512MB RAM (Playwright needs memory)
4. **Port:** The app automatically uses the `PORT` environment variable provided by Render

## Testing Deployment

After deployment, test the health endpoint:

```bash
curl https://your-app-name.onrender.com/health
```

## Troubleshooting

### Build Fails

- Check that Python 3.11+ is available
- Ensure `requirements.txt` is valid
- Check build logs for Playwright installation errors

### App Crashes

- Check logs in Render dashboard
- Verify Playwright browsers are installed
- Ensure sufficient memory allocation

### Timeout Issues

- Increase timeout in Render settings
- Check if scraping operations are taking too long

