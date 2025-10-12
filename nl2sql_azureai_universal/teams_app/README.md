# Deploy NL2SQL Bot to Microsoft Teams

## 📋 Prerequisites
- Bot server running (`python start_server.py`)
- Dev tunnel running (`/opt/homebrew/bin/devtunnel host -p 3978 --allow-anonymous`)
- Azure Bot configured with tunnel URL

## 🎨 Step 1: Create Icon Files

You need two PNG files in this directory:

### `color.png` (192x192 pixels)
- Full color icon for your bot
- Shows in Teams app list
- Can use any image editor or online tool

### `outline.png` (32x32 pixels)  
- Transparent outline icon
- Shows in Teams sidebar
- Should be white/transparent

**Quick way to create icons:**
1. Go to https://www.canva.com or https://www.figma.com
2. Create 192x192px image with text "NL2SQL" and a database icon
3. Export as `color.png`
4. Create 32x32px white icon on transparent background
5. Export as `outline.png`
6. Save both files in this `teams_app` folder

## 📦 Step 2: Create the App Package

Once you have the icon files:

```bash
cd /Users/arturoquiroga/GITHUB/AQ-NEW-NL2SQL/nl2sql_azureai_universal/teams_app
zip -r nl2sql-teams-app.zip manifest.json color.png outline.png
```

## 🚀 Step 3: Upload to Teams

### Option A: Upload for Yourself (Quick Test)
1. Open Microsoft Teams desktop app or web app
2. Click **Apps** in the left sidebar
3. Click **Manage your apps** (bottom left)
4. Click **Upload an app** → **Upload a custom app**
5. Select `nl2sql-teams-app.zip`
6. Click **Add** to install for yourself
7. Start chatting with the bot!

### Option B: Upload for Your Organization (Admin Required)
1. Go to Microsoft Teams Admin Center: https://admin.teams.microsoft.com
2. Navigate to **Teams apps** → **Manage apps**
3. Click **Upload new app**
4. Upload `nl2sql-teams-app.zip`
5. Go to **Manage apps** and find "NL2SQL Bot"
6. Set to **Allowed** or **Available** for users
7. Users can now find it in the Teams app store

### Option C: During Development (Fastest)
1. Open Teams web or desktop app
2. Go to https://teams.microsoft.com
3. Click the **•••** (More added apps) in the left rail
4. Click **More apps**
5. At the bottom, click **Upload a custom app**
6. Choose **Upload for [Your Name]**
7. Select the zip file
8. Click **Add**

## 🧪 Step 4: Test in Teams

After uploading:

1. **Find the bot**: Search for "NL2SQL Bot" in Teams
2. **Start a chat**: Click to open a 1:1 chat
3. **Try queries**:
   ```
   /help
   How many customers do we have?
   Show me the top 5 loans by amount
   ```

## 🔧 Troubleshooting

### Bot doesn't respond
- ✅ Check bot server is running: `http://localhost:3978`
- ✅ Check dev tunnel is running: `https://2kzs3w3z-3978.use.devtunnels.ms`
- ✅ Verify Azure Bot messaging endpoint matches tunnel URL
- ✅ Check terminal logs for errors

### Can't upload app package
- ✅ Make sure both icon files exist
- ✅ Verify icons are correct size (192x192 and 32x32)
- ✅ Check manifest.json has no syntax errors
- ✅ Ensure zip contains all 3 files at root level (not in subfolder)

### Icons don't show
- ✅ Icons must be PNG format
- ✅ Color icon: 192x192px
- ✅ Outline icon: 32x32px, transparent background

## 📝 Important Notes

**Dev Tunnel URL Changes:**
- Every time you restart the dev tunnel, you get a NEW URL
- Update `manifest.json` → `validDomains` with new URL
- Update Azure Bot messaging endpoint with new URL
- Re-zip and re-upload the app package

**For Production:**
- Replace dev tunnel with a permanent public URL (Azure App Service, etc.)
- Update `manifest.json` with production domain
- Publish through proper Teams admin channels

## 🎯 Current Configuration

- **Bot ID**: <YOUR_BOT_ID_HERE>
- **Tenant ID**: <YOUR_TENANT_ID_HERE>
- **Dev Tunnel**: https://2kzs3w3z-3978.use.devtunnels.ms
- **Messaging Endpoint**: https://2kzs3w3z-3978.use.devtunnels.ms/api/messages

## 📚 Additional Resources

- [Teams App Manifest Schema](https://learn.microsoft.com/en-us/microsoftteams/platform/resources/schema/manifest-schema)
- [Upload Custom Apps to Teams](https://learn.microsoft.com/en-us/microsoftteams/platform/concepts/deploy-and-publish/apps-upload)
- [Teams Bot Documentation](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/what-are-bots)
