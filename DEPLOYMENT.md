# Deployment Guide

## Quick Deploy to Streamlit Cloud

### Step 1: Push to GitHub
Your code is already on GitHub at: `https://github.com/CRodriguez245/idea-generator-for-designers.git`

### Step 2: Deploy to Streamlit Cloud

1. Go to [Streamlit Community Cloud](https://share.streamlit.io/)
2. Sign in with your GitHub account
3. Click "New app"
4. Select your repository: `CRodriguez245/idea-generator-for-designers`
5. Set the main file path: `app.py`
6. Click "Deploy"

### Step 3: Configure Secrets

1. In your Streamlit Cloud app dashboard, go to "Settings" → "Secrets"
2. Add your OpenAI API key:
   ```
   OPENAI_API_KEY=sk-proj-...
   ```
3. Save and the app will automatically redeploy

### Step 4: Get Your URL

Once deployed, Streamlit Cloud will provide a URL like:
`https://idea-generator-for-designers.streamlit.app`

This URL will be accessible to anyone and meets the requirement for "accessible via a URL at the time of your final presentation."

## Alternative: Deploy to Other Platforms

### Vercel (if you want a custom domain)
- Requires converting Streamlit app to a different framework (not recommended for this project)

### GitHub Pages
- Not suitable for Python/Streamlit apps (only static sites)

### Recommended: Streamlit Cloud
- Free
- Perfect for Streamlit apps
- Automatic deployments from GitHub
- Built-in secrets management
- Public URL provided

## Post-Deployment Checklist

- [ ] App is accessible via public URL
- [ ] OpenAI API key is configured in Streamlit Cloud secrets
- [ ] Test the app with a sample challenge
- [ ] Verify all features work (generation, refinement, back navigation)
- [ ] Check that images load correctly
- [ ] Test on mobile/tablet if required

## Troubleshooting

**App won't deploy:**
- Check that `requirements.txt` is in the root directory
- Verify Python version compatibility (3.10+)
- Check Streamlit Cloud logs for errors

**API errors:**
- Verify `OPENAI_API_KEY` is set in Streamlit Cloud secrets
- Check API key is valid and has credits

**Slow loading:**
- Normal for first load (cold start)
- Subsequent loads should be faster

