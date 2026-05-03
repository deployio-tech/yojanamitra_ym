import os

files = [
    r"c:\yojanamitra_complete\dashboard.html",
    r"c:\yojanamitra_complete\static\vault.html",
    r"c:\yojanamitra_complete\static\all_schemes.html"
]

for fp in files:
    if os.path.exists(fp):
        with open(fp, "r", encoding="utf-8") as f:
            content = f.read()
        
        # fix the shorthand overriding the dot grid
        content = content.replace("background: var(--page);", "background-color: var(--page);")
        content = content.replace("background: var(--bg-page);", "background-color: var(--bg-page);")
                
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {fp}")
