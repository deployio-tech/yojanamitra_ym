from PIL import Image

try:
    img = Image.open('c:\\scrollyym\\yojana-mitra-backend\\images\\00001.png')
    color = img.getpixel((0, 0))
    # It might be RGBA or RGB
    if isinstance(color, int):
        print(f'#{color:06x}')
    else:
        print(f'#{color[0]:02x}{color[1]:02x}{color[2]:02x}')
except Exception as e:
    print(e)
