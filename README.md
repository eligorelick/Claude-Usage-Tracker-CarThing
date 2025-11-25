# Claude Usage Monitor for Spotify Car Thing

Display your Claude.ai usage limits on a Spotify Car Thing running Nocturne firmware.

**Created by Eli Gorelick** - [eligorelick.com](https://eligorelick.com)

---

## Features

- Real-time display of Claude usage limits
- 5-hour, 7-day, and Sonnet-specific usage tracking  
- Color-coded progress bars (green/yellow/red)
- Warning animation when usage exceeds 80%
- Dark/Light theme toggle
- Live clock display
- Auto-updates every minute

---

## How It Works

```
┌─────────────┐                      ┌─────────────┐
│  Claude.ai  │ <───── Internet ───> │  Windows PC │
│    API      │                      │   Python    │
└─────────────┘                      │   Server    │
                                     └──────┬──────┘
                                            │
                                      USB Cable
                                       (Data)
                                            │
                                     ┌──────▼──────┐
                                     │  Car Thing  │
                                     │             │
                                     │ ┌─────────┐ │
                                     │ │ Display │ │
                                     │ └─────────┘ │
                                     └─────────────┘
```

The Windows PC fetches usage data from Claude's API every 5 minutes and serves it over USB networking. The Car Thing fetches this data and displays it.

---

## Requirements

### Hardware
- Spotify Car Thing
- USB data cable (NOT charge-only - must support data transfer)
- Windows 10/11 PC

### Software  
- Nocturne firmware on Car Thing ([github.com/usenocturne/nocturne-image](https://github.com/usenocturne/nocturne-image))
- Python 3.8 or newer on Windows
- Claude.ai Pro/Team subscription

---

## Setup Guide

### PART 1: Get Your Claude Credentials

Before starting, you need two pieces of information from your Claude account.

#### Step 1.1: Find Your ORG_ID

1. Open Chrome and go to [claude.ai](https://claude.ai)
2. Make sure you're logged in
3. Press `F12` to open Developer Tools
4. Click the **Network** tab
5. Click on any chat or refresh the page
6. Look for any request to `claude.ai/api/organizations/`
7. The URL will contain your org ID, like:
   ```
   claude.ai/api/organizations/3746c04e-9223-4bde-a29f-39db3e23bfea/...
   ```
8. Copy that ID (the part between `organizations/` and the next `/`)

#### Step 1.2: Find Your SESSION_KEY

1. In the same Developer Tools window, click the **Application** tab
2. In the left sidebar, expand **Cookies**
3. Click on `https://claude.ai`
4. Find the row named `sessionKey`
5. Double-click the **Value** column to select it
6. Copy the entire value (starts with `sk-ant-sid01-`)

**Save both values somewhere - you'll need them soon!**

---

### PART 2: Windows Setup

#### Step 2.1: Install Python Dependencies

Open PowerShell and run:

```powershell
pip install curl_cffi flask
```

If you get an error, make sure Python is installed: [python.org/downloads](https://python.org/downloads)

#### Step 2.2: Download and Configure the Server

1. Create a folder: `C:\claude-usage-server\`

2. Copy these files from the `windows` folder:
   - `claude_usage_server.py`
   - `start-server.bat`

3. Open `claude_usage_server.py` in Notepad or any text editor

4. Find these lines near the top (around line 25):
   ```python
   ORG_ID = "YOUR_ORG_ID_HERE"
   SESSION_KEY = "YOUR_SESSION_KEY_HERE"
   ```

5. Replace with your actual values:
   ```python
   ORG_ID = "3746c04e-9223-4bde-a29f-39db3e23bfea"
   SESSION_KEY = "sk-ant-sid01-xxxxx..."
   ```

6. Save the file

#### Step 2.3: Test the Server

1. Double-click `start-server.bat`
2. You should see:
   ```
   Server: http://172.16.42.1:8080
   [HH:MM:SS] Fetching usage from Claude.ai...
   [HH:MM:SS] SUCCESS!
              5-Hour: XX% | 7-Day: XX% | Sonnet: XX%
   ```

If you see errors, check that your ORG_ID and SESSION_KEY are correct.

**Keep this window open - the server needs to be running!**

---

### PART 3: USB Network Setup (Windows)

The Car Thing connects via USB and creates a virtual network adapter.

#### Step 3.1: Connect the Car Thing

1. Plug the Car Thing into your PC via USB
2. Wait for Windows to recognize it (may take 30 seconds)
3. The Car Thing should boot up showing Nocturne

#### Step 3.2: Find the Network Adapter Name

Open PowerShell and run:

```powershell
Get-NetAdapter
```

Look for an adapter with one of these names:
- "Ethernet 2" or "Ethernet 3"
- "Remote NDIS Compatible Device"
- "USB Ethernet/RNDIS Gadget"

Note the exact name (e.g., `Ethernet 3`)

#### Step 3.3: Set Static IP

Run this command (replace `Ethernet 3` with your adapter name):

```powershell
netsh interface ip set address "Ethernet 3" static 172.16.42.1 255.255.255.0
```

#### Step 3.4: Enable Internet Sharing

1. Open **Control Panel** > **Network and Sharing Center**
2. Click your main internet connection (WiFi or Ethernet - NOT the Car Thing)
3. Click **Properties**
4. Go to **Sharing** tab
5. Check **"Allow other network users to connect through this computer's Internet connection"**
6. If there's a dropdown, select the Car Thing adapter
7. Click **OK**

#### Step 3.5: Test Connection

```powershell
ping 172.16.42.2
```

If you get replies, the connection is working!

---

### PART 4: Car Thing Setup

#### Step 4.1: Connect via SSH

Open PowerShell and run:

```powershell
ssh root@172.16.42.2
```

Password: `nocturne`

#### Step 4.2: Make Filesystem Writable

```bash
mount -o remount,rw /
```

#### Step 4.3: Create Directories

```bash
mkdir -p /opt/custom
mkdir -p /etc/sv/usage-fetcher
mkdir -p /etc/sv/usage-http
```

#### Step 4.4: Create the Scripts

Run each of these commands:

**Fetch Script:**
```bash
cat > /opt/custom/fetch-usage.sh << 'EOF'
#!/bin/sh
while true; do
    curl -s "http://172.16.42.1:8080/" > /tmp/usage.json 2>/dev/null
    sleep 60
done
EOF
```

**HTTP Server Script:**
```bash
cat > /opt/custom/http-server.sh << 'EOF'
#!/bin/sh
while true; do
    { 
        read request
        echo -e "HTTP/1.1 200 OK\r\nAccess-Control-Allow-Origin: *\r\nContent-Type: application/json\r\nConnection: close\r\n"
        cat /tmp/usage.json 2>/dev/null || echo '{"error":"no data"}'
    } | nc -l -p 8080
done
EOF
```

**Boot Script:**
```bash
cat > /etc/rc.local << 'EOF'
#!/bin/sh
mount -o remount,rw /
sleep 10
ntpd -n -q -p pool.ntp.org &
EOF
```

**Service Scripts:**
```bash
cat > /etc/sv/usage-fetcher/run << 'EOF'
#!/bin/sh
exec /opt/custom/fetch-usage.sh
EOF

cat > /etc/sv/usage-http/run << 'EOF'
#!/bin/sh
exec /opt/custom/http-server.sh
EOF
```

#### Step 4.5: Create the Display HTML

This is a long command - copy the entire thing:

```bash
cat > /opt/custom/claude-usage-display.html << 'HTMLEOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Usage Monitor</title>
    <style>
        :root {
            --bg-primary: #0a0a0a;
            --bg-card: #111111;
            --border-color: #222;
            --text-primary: #f5f5f5;
            --text-secondary: #888;
            --text-muted: #555;
            --accent: #ff6b00;
            --green: #22c55e;
            --yellow: #eab308;
            --red: #ef4444;
        }
        .light-theme {
            --bg-primary: #f5f5f5;
            --bg-card: #ffffff;
            --border-color: #e0e0e0;
            --text-primary: #1a1a1a;
            --text-secondary: #555;
            --text-muted: #888;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            height: 480px;
            width: 800px;
            overflow: hidden;
            padding: 15px;
            transition: background 0.3s, color 0.3s;
        }
        .container { display: flex; flex-direction: column; height: 100%; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-shrink: 0; }
        h1 { font-size: 26px; color: var(--accent); font-weight: 300; letter-spacing: 2px; }
        .header-right { display: flex; align-items: center; gap: 12px; }
        .clock { font-size: 20px; color: var(--text-secondary); font-variant-numeric: tabular-nums; }
        .controls { display: flex; gap: 6px; }
        .btn { background: var(--bg-card); border: 1px solid var(--border-color); color: var(--text-secondary); padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 14px; }
        .main-grid { display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 12px; flex: 1; min-height: 0; }
        .usage-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 18px; display: flex; flex-direction: column; justify-content: space-between; }
        .usage-card.warning { animation: pulse-warning 2s infinite; border-color: var(--red); }
        @keyframes pulse-warning { 0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); } 50% { box-shadow: 0 0 20px 5px rgba(239, 68, 68, 0.3); } }
        .usage-header { display: flex; justify-content: space-between; align-items: center; }
        .usage-title { font-size: 14px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px; }
        .usage-value { font-size: 42px; font-weight: 700; }
        .usage-value.green { color: var(--green); }
        .usage-value.yellow { color: var(--yellow); }
        .usage-value.red { color: var(--red); }
        .progress-bar { width: 100%; height: 12px; background: var(--border-color); border-radius: 6px; overflow: hidden; margin: 12px 0; }
        .progress-fill { height: 100%; border-radius: 6px; transition: width 1s ease-out; }
        .progress-fill.green { background: var(--green); }
        .progress-fill.yellow { background: var(--yellow); }
        .progress-fill.red { background: var(--red); }
        .reset-info { font-size: 13px; color: var(--text-muted); }
        .reset-time { color: var(--text-secondary); font-weight: 500; }
        .credit-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 18px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
        .smiley { font-size: 48px; margin-bottom: 10px; color: var(--accent); }
        .credit-name { font-size: 16px; color: var(--text-secondary); margin-bottom: 5px; }
        .credit-site { font-size: 14px; color: var(--accent); text-decoration: none; }
        .footer { display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: var(--text-muted); margin-top: 12px; flex-shrink: 0; }
        .status-dot { display: inline-block; width: 6px; height: 6px; background: var(--green); border-radius: 50%; margin-right: 5px; animation: blink 2s infinite; }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .error { background: #1a0a0a; border: 1px solid var(--red); padding: 30px; border-radius: 10px; text-align: center; font-size: 18px; color: var(--red); flex: 1; display: flex; align-items: center; justify-content: center; }
        .loading { text-align: center; font-size: 20px; color: var(--accent); flex: 1; display: flex; align-items: center; justify-content: center; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Claude Usage</h1>
            <div class="header-right">
                <div class="clock" id="clock">--:--:--</div>
                <div class="controls">
                    <button class="btn" id="themeBtn" onclick="toggleTheme()">Light</button>
                </div>
            </div>
        </div>
        <div id="content"><div class="loading">Loading...</div></div>
    </div>
    <script>
        const REFRESH_INTERVAL = 60 * 1000;
        let isLightTheme = false;
        function updateClock() { document.getElementById('clock').textContent = new Date().toLocaleTimeString(); }
        setInterval(updateClock, 1000);
        updateClock();
        function toggleTheme() {
            isLightTheme = !isLightTheme;
            document.body.classList.toggle('light-theme', isLightTheme);
            document.getElementById('themeBtn').textContent = isLightTheme ? 'Dark' : 'Light';
        }
        function getColorClass(percent) { if (percent < 50) return 'green'; if (percent < 80) return 'yellow'; return 'red'; }
        function formatResetAsClock(resetAt) { if (!resetAt) return 'N/A'; return new Date(resetAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }
        function formatResetDuration(resetAt) {
            if (!resetAt) return 'N/A';
            const diffMs = new Date(resetAt) - new Date();
            if (diffMs < 0) return 'Soon';
            const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
            const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
            if (diffHours > 24) return Math.floor(diffHours / 24) + 'd ' + (diffHours % 24) + 'h';
            return diffHours + 'h ' + diffMins + 'm';
        }
        async function fetchUsage() {
            try {
                const response = await fetch('http://localhost:8080/usage');
                if (!response.ok) throw new Error('HTTP ' + response.status);
                const data = await response.json();
                if (data.error) throw new Error(data.error);
                if (data.status) throw new Error('Waiting for data...');
                displayUsage(data);
            } catch (error) { displayError(error.message); }
        }
        function displayUsage(data) {
            const contentDiv = document.getElementById('content');
            let html = '<div class="main-grid">';
            if (data.five_hour) {
                const p = Math.min(100, data.five_hour.utilization || 0);
                const c = getColorClass(p);
                html += '<div class="usage-card' + (p >= 80 ? ' warning' : '') + '"><div class="usage-header"><div class="usage-title">5-Hour Limit</div><div class="usage-value ' + c + '">' + p.toFixed(0) + '%</div></div><div class="progress-bar"><div class="progress-fill ' + c + '" style="width:' + p + '%"></div></div><div class="reset-info">Resets at <span class="reset-time">' + formatResetAsClock(data.five_hour.resets_at) + '</span> (' + formatResetDuration(data.five_hour.resets_at) + ')</div></div>';
            }
            if (data.seven_day) {
                const p = Math.min(100, data.seven_day.utilization || 0);
                const c = getColorClass(p);
                html += '<div class="usage-card' + (p >= 80 ? ' warning' : '') + '"><div class="usage-header"><div class="usage-title">7-Day Limit</div><div class="usage-value ' + c + '">' + p.toFixed(0) + '%</div></div><div class="progress-bar"><div class="progress-fill ' + c + '" style="width:' + p + '%"></div></div><div class="reset-info">Resets at <span class="reset-time">' + formatResetAsClock(data.seven_day.resets_at) + '</span> (' + formatResetDuration(data.seven_day.resets_at) + ')</div></div>';
            }
            if (data.seven_day_sonnet) {
                const p = Math.min(100, data.seven_day_sonnet.utilization || 0);
                const c = getColorClass(p);
                html += '<div class="usage-card' + (p >= 80 ? ' warning' : '') + '"><div class="usage-header"><div class="usage-title">Sonnet 7-Day</div><div class="usage-value ' + c + '">' + p.toFixed(0) + '%</div></div><div class="progress-bar"><div class="progress-fill ' + c + '" style="width:' + p + '%"></div></div><div class="reset-info">Resets at <span class="reset-time">' + formatResetAsClock(data.seven_day_sonnet.resets_at) + '</span> (' + formatResetDuration(data.seven_day_sonnet.resets_at) + ')</div></div>';
            }
            html += '<div class="credit-card"><div class="smiley">: )</div><div class="credit-name">Created by Eli Gorelick</div><div class="credit-site">eligorelick.com</div></div>';
            html += '</div>';
            html += '<div class="footer"><div><span class="status-dot"></span>Live - Updates every minute</div><div>Last updated: ' + new Date().toLocaleTimeString() + '</div></div>';
            contentDiv.innerHTML = html;
        }
        function displayError(message) { document.getElementById('content').innerHTML = '<div class="error">Error: ' + message + '</div><div class="footer" style="margin-top:12px"><div>Retrying...</div><div>' + new Date().toLocaleTimeString() + '</div></div>'; }
        fetchUsage();
        setInterval(fetchUsage, REFRESH_INTERVAL);
    </script>
</body>
</html>
HTMLEOF
```

#### Step 4.6: Make Scripts Executable

```bash
chmod +x /opt/custom/*.sh
chmod +x /etc/sv/usage-fetcher/run
chmod +x /etc/sv/usage-http/run
chmod +x /etc/rc.local
```

#### Step 4.7: Enable Services

```bash
ln -sf /etc/sv/usage-fetcher /var/service/usage-fetcher
ln -sf /etc/sv/usage-http /var/service/usage-http
```

#### Step 4.8: Configure Chromium to Show the Display

Find out how Chromium is configured:

```bash
cat /etc/sv/chromium/run
```

You need to modify it to open our HTML file. The URL should be:

```
file:///opt/custom/claude-usage-display.html
```

#### Step 4.9: Start Everything

```bash
sv restart usage-fetcher
sv restart usage-http
sv restart chromium
```

---

### PART 5: Verify It's Working

#### On Windows:
The PowerShell window should show:
```
[HH:MM:SS] SUCCESS!
           5-Hour: XX% | 7-Day: XX%
```

#### On Car Thing SSH:
```bash
curl http://172.16.42.1:8080/    # Should show JSON data
curl http://localhost:8080/       # Should show same data
cat /tmp/usage.json              # Should have data
```

#### On the Display:
You should see your Claude usage with colored progress bars!

---

## Auto-Start on Windows Boot

To make the server start automatically when you log in:

1. Press `Win + R`
2. Type `shell:startup` and press Enter
3. Copy `start-server.bat` into the folder that opens

---

## Troubleshooting

### "Error: Waiting for data..."
- Make sure the Windows Python server is running
- Check that `ping 172.16.42.1` works from Car Thing

### USB Connection Issues
- Try a different USB cable (must be data cable, not charge-only)
- Try a different USB port (USB 2.0 ports often work better)
- After reconnecting, you may need to set the IP again

### Session Expired
- Get a new SESSION_KEY from browser cookies
- Update `claude_usage_server.py`
- Restart the Python server

### Display Not Updating
- Run `sv restart chromium` on Car Thing
- Check if services are running: `sv status usage-fetcher`

### Time Shows Wrong
- Car Thing has no battery clock, syncs on boot
- Manual sync: `ntpd -n -q -p pool.ntp.org`

---

## Useful Commands

```bash
# Instant display refresh
sv restart chromium

# Check services
sv status usage-fetcher
sv status usage-http

# View current data
cat /tmp/usage.json

# Test Windows connection
curl http://172.16.42.1:8080/

# Manual time sync
ntpd -n -q -p pool.ntp.org

# Remount filesystem (if needed after reboot)
mount -o remount,rw /
```

---

## File Structure

```
claude-carthing/
├── README.md                    # This file
├── windows/
│   ├── claude_usage_server.py   # Python server (edit with your credentials)
│   └── start-server.bat         # Double-click to start
└── carthing/
    ├── opt-custom/
    │   ├── fetch-usage.sh       # Fetches data from Windows
    │   ├── http-server.sh       # Serves data to display
    │   └── claude-usage-display.html  # The UI
    ├── etc/
    │   └── rc.local             # Boot script
    └── etc-sv/
        ├── usage-fetcher/run    # Service definition
        └── usage-http/run       # Service definition
```

---

## Credits

**Created by Eli Gorelick**
- Website: [eligorelick.com](https://eligorelick.com)

Built with help from Claude AI.

---

## License

MIT License - Feel free to modify and share!
