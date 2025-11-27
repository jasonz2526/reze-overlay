from PIL import Image, ImageDraw, ImageFont

def overlay_text(image_path, bubbles):
    """
    bubbles: list of dicts [{bbox: (x1,y1,x2,y2), text: "translated text"}]
    """
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    
    for bubble in bubbles:
        x1, y1, x2, y2 = bubble['bbox']
        draw.rounded_rectangle((x1, y1, x2, y2), fill="white", radius=10)
        draw.text((x1+5, y1+5), bubble['text'], fill="black", font=font)
    
    img.show()
