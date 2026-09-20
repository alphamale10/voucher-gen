import io
import os
import random
import zipfile
import tempfile
from flask import Flask, render_template_string, request, send_file, jsonify
from PIL import Image
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)
# ==========================================
# SECURITY (CHANGE THESE)
# ==========================================
AUTH_USERNAME = "Waitrose"
AUTH_PASSWORD = "hassan_zimmy"

from flask import Response

@app.before_request
def require_login():
    auth = request.authorization
    if not auth or not (auth.username == AUTH_USERNAME and auth.password == AUTH_PASSWORD):
        return Response(
            'Login required.', 401,
            {'WWW-Authenticate': 'Basic realm="Voucher Generator"'}
        )

# ==========================================
# CONFIGURATION (RELATIVE PATH FOR CLOUD)
# ==========================================
TEMPLATE_PATH = "waitrose_template.png.png"
BBOX = (201, 1283, 734, 1456) 
PREFIX = "994183"
SUFFIX = "750"
# ==========================================

def generate_barcode(ref_number):
    ref_str = str(ref_number).zfill(3) 
    base_12 = f"{PREFIX}{ref_str}{SUFFIX}"
    EAN = barcode.get_barcode_class('ean13')
    ean = EAN(base_12, writer=ImageWriter())
    buffer = io.BytesIO()
    ean.write(buffer, options={"write_text": False, "module_height": 15.0, "module_width": 0.3})
    buffer.seek(0)
    return Image.open(buffer)

def create_voucher_image(ref_number):
    barcode_img = generate_barcode(ref_number)
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError("Template not found. Check the path.")
    template = Image.open(TEMPLATE_PATH)
    bbox_width = BBOX[2] - BBOX[0]
    bbox_height = BBOX[3] - BBOX[1]
    barcode_img = barcode_img.resize((bbox_width, bbox_height), Image.Resampling.LANCZOS)
    template.paste(barcode_img, (BBOX[0], BBOX[1]))
    return template

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Voucher Generator</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f4f4f9; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }
        .container { background: white; padding: 30px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; width: 100%; max-width: 350px; }
        h1 { margin-top: 0; color: #333; font-size: 22px; }
        p { color: #666; font-size: 14px; margin-bottom: 24px; }
        input[type="number"] { width: 100%; padding: 14px; font-size: 16px; border: 1px solid #ccc; border-radius: 8px; text-align: center; margin-bottom: 16px; box-sizing: border-box; }
        button { background: #4a7c3f; color: white; border: none; padding: 16px 24px; font-size: 16px; border-radius: 8px; cursor: pointer; width: 100%; font-weight: bold; }
        .status { margin-top: 16px; font-size: 13px; color: #4a7c3f; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Waitrose Voucher Gen</h1>
        <p>Enter how many vouchers you need.</p>
        <form id="genForm">
            <input type="number" id="amount" value="5" min="1" max="100" required>
            <button type="submit" id="genBtn">Generate & Download</button>
        </form>
        <div class="status" id="status"></div>
    </div>
    <script>
        document.getElementById('genForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('genBtn');
            const status = document.getElementById('status');
            btn.disabled = true; btn.textContent = "Generating...";
            status.textContent = "Please wait, this may take a moment.";
            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ amount: parseInt(document.getElementById('amount').value) })
                });
                if (!response.ok) throw new Error('Server error');
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = 'waitrose_vouchers.zip';
                document.body.appendChild(a); a.click(); a.remove();
                window.URL.revokeObjectURL(url);
                status.textContent = "Download started! Check your Files app.";
            } catch (err) {
                status.textContent = "Error: " + err.message;
            } finally {
                btn.disabled = false; btn.textContent = "Generate & Download";
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    amount = data.get('amount', 5)
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_buffer = io.BytesIO()
        used_refs = set()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for i in range(1, amount + 1):
                while True:
                    random_ref = random.randint(100, 999)
                    if random_ref not in used_refs:
                        used_refs.add(random_ref)
                        break
                img = create_voucher_image(random_ref)
                img_filename = f"£7.50 Ref_{random_ref}.png"
                img_path = os.path.join(tmpdir, img_filename)
                img.save(img_path)
                zip_file.write(img_path, img_filename)
        zip_buffer.seek(0)
        return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='waitrose_vouchers.zip')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)