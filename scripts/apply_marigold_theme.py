import os

files = [
    r"c:\yojanamitra_complete\dashboard.html",
    r"c:\yojanamitra_complete\static\vault.html",
    r"c:\yojanamitra_complete\static\all_schemes.html"
]

mappings = {
    # 1. Variables in :root
    "--blue: #1a56db;": "--blue: #e69000;",
    "--blue-hover: #1442b5;": "--blue-hover: #c97a0a;",
    "--blue-soft: #eff4ff;": "--blue-soft: #fff5e1;",
    "--blue-mid: #dce8ff;": "--blue-mid: #ffe0b2;",

    "--accent: #5560f5;": "--accent: #ffa000;",
    "--accent-dark: #3d47d4;": "--accent-dark: #e69000;",
    "--accent-light: #eef0ff;": "--accent-light: #fff5e1;",

    "--page: #f6f8fc;": "--page: #c9ded0;",
    "--bg-page: #f4f5fb;": "--bg-page: #c9ded0;",
    "--bg-hero: #eef0f9;": "--bg-hero: #bbd2c4;",

    "--ink: #111827;": "--ink: #0b1a16;",
    "--ink-2: #374151;": "--ink-2: #2d3a35;",
    "--text-dark: #0f1117;": "--text-dark: #0b1a16;",
    "--text-mid: #4b5263;": "--text-mid: #2d3a35;",
    "--text-muted: #8a92a6;": "--text-muted: #5a6a64;",
    "--muted: #6b7280;": "--muted: #5a6a64;",
    "--muted-2: #9ca3af;": "--muted-2: #a1b0a8;",

    "--line: #e5e7eb;": "--line: #cbe0d4;",
    "--border: #e4e6f0;": "--border: #d1dbd5;",
    "--line-2: #f3f4f6;": "--line-2: #e0ebd5;",
    "--surface: #f9fafb;": "--surface: #f0f5ec;",
    
    # 2. Hardcoded colors
    "rgba(85, 96, 245": "rgba(255, 160, 0", 
    "rgba(85,96,245": "rgba(255,160,0",
    "rgba(26, 86, 219": "rgba(230, 144, 0", 
    "rgba(37, 99, 235": "rgba(230, 144, 0", 
    "rgba(59, 130, 246": "rgba(255, 160, 0", 

    "#5560f5": "#ffa000",
    "#1a56db": "#e69000",
    "#1442b5": "#c97a0a",
    "#3b82f6": "#ffa000",
    "#1d4ed8": "#e69000",
    "#2563eb": "#ffa000",
    "#4f46e5": "#ffa000",
    "#4338ca": "#e69000",

    "#eff6ff": "#fff5e1",
    "#f1f5f9": "#f0f5ec",
    "#f8fafc": "#f5faf0",
    "#cbd5e1": "#b2c1b9",
    "#e2e8f0": "#cbe0d4",
    "#94a3b8": "#90a299",
    "#0f172a": "#0b1a16",
    "#334155": "#2d3a35",
    "#1e293b": "#162822",
    "#64748b": "#5a6a64",

    "linear-gradient(to right, #dce8ff, #1a56db)": "linear-gradient(to right, #ffe0b2, #ffa000)",
}

for fp in files:
    if os.path.exists(fp):
        with open(fp, "r", encoding="utf-8") as f:
            content = f.read()
        
        for k, v in mappings.items():
            content = content.replace(k, v)
        
        # In all files, let's look for CSS body tag and add dot grid if missing
        if "rgba(11, 26, 22, 0.05) 1.5px" not in content and "body {" in content:
            # specifically locate the body block
            # we'll inject background-image into the body styles
            parts = content.split("body {")
            if len(parts) > 1:
                # prepend the background styles to the first properties in body
                dots = "\n      background-image: radial-gradient(rgba(11, 26, 22, 0.05) 1.5px, transparent 1.5px);\n      background-size: 32px 32px;"
                content = parts[0] + "body {" + dots + parts[1]
                
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {fp}")
    else:
        print(f"File not found: {fp}")
