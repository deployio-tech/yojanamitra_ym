const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');

let mainWindow;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 380,
        height: 600,
        frame: false,
        transparent: true,
        backgroundColor: '#00000000',
        alwaysOnTop: true,
        resizable: false,
        hasShadow: false,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        }
    });

    mainWindow.loadFile('index.html');
    
    // Default to compact size bounds
    const { screen } = require('electron');
    const primaryDisplay = screen.getPrimaryDisplay();
    const { width, height } = primaryDisplay.workAreaSize;
    
    // initial small pill mode
    mainWindow.setBounds({ x: width - 80, y: height - 80, width: 60, height: 60 });

    ipcMain.on('resize-window', (event, mode) => {
        const bounds = mainWindow.getBounds();
        const screenWidth = primaryDisplay.workAreaSize.width;
        const screenHeight = primaryDisplay.workAreaSize.height;
        
        let newW, newH, newX, newY;
        
        if (mode === 'expanded') {
            newW = 340;
            newH = 500;
            // Expand upwards and leftwards if near bottom right, else just expand
            newX = bounds.x;
            newY = bounds.y;
            
            // Adjust if goes off screen
            if (newX + newW > screenWidth) newX = screenWidth - newW - 10;
            if (newY + newH > screenHeight) newY = screenHeight - newH - 10;
        } else {
            newW = 60;
            newH = 60;
            newX = bounds.x;
            newY = bounds.y;
        }
        
        mainWindow.setBounds({
            x: Math.max(10, newX),
            y: Math.max(10, newY),
            width: newW,
            height: newH
        });
    });
    ipcMain.on('hide-window', () => {
        mainWindow.hide();
    });
}

app.whenReady().then(() => {
    createWindow();
    
    // Start local server to receive launch signals and data from the web app
    const http = require('http');
    http.createServer((req, res) => {
        // Handle CORS
        res.setHeader('Access-Control-Allow-Origin', '*');
        res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
        
        if (req.method === 'OPTIONS') {
            res.writeHead(204);
            res.end();
            return;
        }

        if (req.url === '/launch') {
            let body = '';
            req.on('data', chunk => { body += chunk.toString(); });
            req.on('end', () => {
                if (mainWindow) {
                    // Reload to ensure latest changes, then wait for load to send data
                    mainWindow.loadFile('index.html');
                    mainWindow.show();
                    
                    mainWindow.webContents.once('did-finish-load', () => {
                        mainWindow.webContents.send('force-expanded');
                        if (body) {
                            try {
                                const data = JSON.parse(body);
                                if (data.profile) {
                                    mainWindow.webContents.send('profile-data', data.profile);
                                }
                            } catch (e) {}
                        }
                    });
                }
                res.writeHead(200);
                res.end(JSON.stringify({ status: 'ok' }));
            });
        }
 else {
            res.writeHead(404);
            res.end();
        }
    }).listen(33262, '127.0.0.1');
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});
