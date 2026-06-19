from flask import Flask, render_template, request, send_file
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import io

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    # 1. Fetch images and inputs
    front_file = request.files.get('front')
    back_file = request.files.get('back')
    num_cards = int(request.form.get('num_cards', 1))
    padding_mm = float(request.form.get('padding', 2))

    # Stricter check: Make sure files exist AND have a filename
    if not front_file or front_file.filename == '' or not back_file or back_file.filename == '':
        return "ERROR: Flask did not receive the images. Please check that you selected both files and that your HTML form includes enctype='multipart/form-data'. Go back and try again.", 400

    # Open images using Pillow (supports png, jpeg, etc.)
    front_img = Image.open(front_file.stream)
    back_img = Image.open(back_file.stream)
    
    front_reader = ImageReader(front_img)
    back_reader = ImageReader(back_img)

    # Limit to 10 cards (A4 comfortably fits a 2x5 grid of standard cards)
    num_cards = min(num_cards, 10)
    
    # Pad to even number for proper grid alignment (avoids file type issues with odd numbers)
    display_cards = num_cards if num_cards % 2 == 0 else num_cards + 1

    # 2. Define standard dimensions with padding (85mm x 55mm is standard A4 card size)
    padding = padding_mm * mm
    base_card_w = 85 * mm
    base_card_h = 55 * mm
    
    # Space per card includes padding on all sides, but we subtract it from card dimensions
    # to keep content within the grid area
    card_w = base_card_w - (2 * padding)
    card_h = base_card_h - (2 * padding)
    spacing_w = base_card_w  # Total space per card horizontally
    spacing_h = base_card_h  # Total space per card vertically
    
    a4_w, a4_h = A4

    # 3. Calculate perfectly centered margins for a 2x5 grid
    # This centering is strictly required so flipping the paper perfectly aligns the margins.
    margin_left = (a4_w - (2 * spacing_w)) / 2
    margin_top = (a4_h - (5 * spacing_h)) / 2

    # 4. Initialize PDF
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)

    # --- PAGE 1: FRONT FACES ---
    for i in range(display_cards):
        col = i % 2     # Column 0 (Left) or 1 (Right)
        row = i // 2    # Row 0 to 4 (Top to Bottom)
        
        x_base = margin_left + (col * spacing_w)
        y_base = a4_h - margin_top - ((row + 1) * spacing_h)
        
        # Add padding offset to position image inside the card space
        x = x_base + padding
        y = y_base + padding
        
        if i < num_cards:
            # Draw front image
            p.drawImage(ImageReader(front_img.copy()), x, y, width=card_w, height=card_h, preserveAspectRatio=False)
        else:
            # explicitly draw a white space to balance the grid
            p.setFillColorRGB(1, 1, 1) # White
            p.rect(x, y, card_w, card_h, fill=1, stroke=0)
    
    p.showPage() # End Page 1

    # --- PAGE 2: BACK FACES ---
    for i in range(display_cards):
        col = i % 2
        row = i // 2
        
        # Calculate where the front was
        x_front_base = margin_left + (col * spacing_w)
        
        # The Mirroring Logic: 
        x_back_base = a4_w - x_front_base - spacing_w
        
        y_base = a4_h - margin_top - ((row + 1) * spacing_h)
        
        # Add padding offset
        x = x_back_base + padding
        y = y_base + padding
        
        if i < num_cards:
            # Draw back image
            p.drawImage(ImageReader(back_img.copy()), x, y, width=card_w, height=card_h, preserveAspectRatio=False)
        else:
            # explicitly draw a white space to balance the grid
            p.setFillColorRGB(1, 1, 1) # White
            p.rect(x, y, card_w, card_h, fill=1, stroke=0)
    
    p.showPage()  # End Page 2
        
    p.save()
    buffer.seek(0)

    # 5. Serve the PDF to the user
    return send_file(
        buffer,
        as_attachment=True,
        download_name='business_cards_ready_to_print.pdf',
        mimetype='application/pdf'
    )

if __name__ == '__main__':
    app.run(debug=True)