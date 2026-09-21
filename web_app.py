import io
import os
import re
import random
import zipfile
import tempfile
from flask import Flask, render_template_string, request, send_file, jsonify, Response
from PIL import Image
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)

# ==========================================
# SECURITY (CHANGE THESE)
# ==========================================
AUTH_USERNAME = "friend"
AUTH_PASSWORD = "waitrose2026"

@app.before_request
def require_login():
    if request.path == '/health':
        return
    auth = request.authorization
    if not auth or not (auth.username == AUTH_USERNAME and auth.password == AUTH_PASSWORD):
        return Response(
            'Login required.', 401,
            {'WWW-Authenticate': 'Basic realm="Voucher Generator"'}
        )

@app.route('/health')
def health():
    return "OK", 200

# ==========================================
# CONFIGURATION
# ==========================================
TEMPLATES = {
    "150": "£1.50 template.png",
    "200": "£2.00 template.png",
    "300": "£3.00 template.png",
    "400": "£4.00 template.png",
    "500": "£5.00 template.png",
    "600": "£6.00 template.png",
    "750": "£7.50 template.png",
    "800": "£8.00 template.png",
}

BBOX = (201, 1283, 734, 1456)
PREFIX = "994183"
# ==========================================


def format_amount_label(amount_code):
    return f"£{int(amount_code) / 100:.2f}"


def generate_barcode_image(amount_code, ref_code):
    base_12 = f"{PREFIX}{ref_code}{amount_code}"
    EAN = barcode.get_barcode_class('ean13')
    ean = EAN(base_12, writer=ImageWriter())
    buffer = io.BytesIO()
    ean.write(buffer, options={
        "write_text": False,
        "module_height": 15.0,
        "module_width": 0.3
    })
    buffer.seek(0)
    return Image.open(buffer)


def compose_voucher(amount_code, ref_code):
    barcode_img = generate_barcode_image(amount_code, ref_code)
    template_path = TEMPLATES.get(amount_code)
    if not template_path or not os.path.exists(template_path):
        raise FileNotFoundError(f"Template for {format_amount_label(amount_code)} not found.")
    template = Image.open(template_path)
    w = BBOX[2] - BBOX[0]
    h = BBOX[3] - BBOX[1]
    barcode_img = barcode_img.resize((w, h), Image.Resampling.LANCZOS)
    template.paste(barcode_img, (BBOX[0], BBOX[1]))
    return template


def pick_unique_refs(count):
    pool = list(range(100, 1000))
    random.shuffle(pool)
    return [f"{n:03d}" for n in pool[:count]]


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Voucher Generator</title>
<style>
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         background: #f4f4f9; margin: 0; padding: 20px; min-height: 100vh; }
  .container { background: white; padding: 24px; border-radius: 16px;
               box-shadow: 0 4px 12px rgba(0,0,0,0.08); max-width: 420px; margin: 0 auto; }
  h1 { margin: 0 0 4px; font-size: 20px; color: #2e7d32; text-align: center; }
  .sub { text-align: center; font-size: 12px; color: #888; margin-bottom: 20px; }
  fieldset { border: 1px solid #ddd; border-radius: 8px; padding: 12px 16px; margin: 0 0 16px; }
  legend { font-weight: 600; font-size: 13px; color: #444; padding: 0 6px; }
  .row { display: flex; align-items: center; padding: 6px 0; font-size: 15px; }
  .row input[type="radio"] { margin-right: 10px; }
  .row label { cursor: pointer; flex: 1; }
  .row.custom input[type="text"] { width: 70px; padding: 6px; font-size: 14px;
                                    border: 1px solid #ccc; border-radius: 6px;
                                    text-align: center; }
  .row.custom .hint { font-size: 11px; color: #999; margin-left: 8px; }
  .qty-input { width: 80px; padding: 10px; font-size: 15px; border: 1px solid #ccc;
               border-radius: 6px; text-align: center; margin-top: 6px; }
  button { background: #4a7c3f; color: white; border: none; padding: 14px;
           font-size: 16px; border-radius: 8px; cursor: pointer; width: 100%;
           font-weight: bold; margin-top: 8px; transition: background 0.2s; }
  button:active { background: #3e6834; }
  button:disabled { background: #9cb89a; cursor: not-allowed; }
  .status { text-align: center; margin-top: 14px; font-size: 13px; min-height: 18px; }
  .status.ok { color: #2e7d32; }
  .status.err { color: #c62828; }
</style>
</head>
<body>
<div class="container">
  <h1>Waitrose Voucher Gen</h1>
  <div class="sub">Select an amount and quantity, then download.</div>

  <form id="genForm">
    <fieldset>
      <legend>Coupon Amount</legend>
      <div class="row"><input type="radio" name="amt" value="150" id="a150" checked><label for="a150">£1.50</label></div>
      <div class="row"><input type="radio" name="amt" value="200" id="a200"><label for="a200">£2.00</label></div>
      <div class="row"><input type="radio" name="amt" value="300" id="a300"><label for="a300">£3.00</label></div>
      <div class="row"><input type="radio" name="amt" value="400" id="a400"><label for="a400">£4.00</label></div>
      <div class="row"><input type="radio" name="amt" value="500" id="a500"><label for="a500">£5.00</label></div>
      <div class="row"><input type="radio" name="amt" value="600" id="a600"><label for="a600">£6.00</label></div>
      <div class="row"><input type="radio" name="amt" value="750" id="a750"><label for="a750">£7.50</label></div>
      <div class="row"><input type="radio" name="amt" value="800" id="a800"><label for="a800">£8.00</label></div>
      <div class="row custom">
        <input type="radio" name="amt" value="custom" id="acustom">
        <label for="acustom">Custom (barcode only):</label>
        <input type="text" id="customVal" maxlength="3" inputmode="numeric" placeholder="250" pattern="\\d{3}">
        <span class="hint">3 digits</span>
      </div>
    </fieldset>

    <fieldset>
      <legend>Quantity</legend>
      <input type="number" id="qty" class="qty-input" value="5" min="1" max="200">
    </fieldset>

    <button type="submit" id="genBtn">Generate &amp; Download</button>
    <div class="status" id="status"></div>
  </form>
</div>

<script>
document.getElementById('genForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('genBtn');
  const status = document.getElementById('status');
  const amtRadio = document.querySelector('input[name="amt"]:checked').value;
  const qty = parseInt(document.getElementById('qty').value);
  const customVal = document.getElementById('customVal').value.trim();

  status.className = 'status';
  status.textContent = '';

  if (!qty || qty < 1 || qty > 200) {
    status.className = 'status err';
    status.textContent = 'Quantity must be 1–200.';
    return;
  }

  let amount;
  let custom = false;
  if (amtRadio === 'custom') {
    if (!/^\\d{3}$/.test(customVal)) {
      status.className = 'status err';
      status.textContent = 'Custom amount must be exactly 3 digits.';
      return;
    }
    amount = customVal;
    custom = true;
  } else {
    amount = amtRadio;
  }

  btn.disabled = true;
  btn.textContent = 'Generating...';
  status.textContent = 'Please wait.';

  try {
    const resp = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount, quantity: qty, custom })
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ error: 'Server error' }));
      throw new Error(err.error || 'Server error');
    }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'waitrose_vouchers.zip';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    status.className = 'status ok';
    status.textContent = 'Download started. Check your Files app.';
  } catch (err) {
    status.className = 'status err';
    status.textContent = 'Error: ' + err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Generate & Download';
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
    amount_code = str(data.get('amount', '750'))
    quantity = int(data.get('quantity', 5))
    custom = bool(data.get('custom', False))

    if quantity < 1 or quantity > 200:
        return jsonify({"error": "Quantity must be 1–200."}), 400

    if not re.fullmatch(r"\d{3}", amount_code):
        return jsonify({"error": "Amount must be 3 digits."}), 400

    if not custom and amount_code not in TEMPLATES:
        return jsonify({"error": "Unknown preset amount."}), 400

    refs = pick_unique_refs(quantity)
    amount_label = format_amount_label(amount_code)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for ref in refs:
                    if custom:
                        img = generate_barcode_image(amount_code, ref)
                        filename = f"Barcode {amount_label} Ref_{ref}.png"
                    else:
                        img = compose_voucher(amount_code, ref)
                        filename = f"{amount_label} Ref_{ref}.png"

                    out_path = os.path.join(tmpdir, filename)
                    img.save(out_path)
                    zf.write(out_path, filename)

            zip_buffer.seek(0)
            return send_file(
                zip_buffer,
                mimetype='application/zip',
                as_attachment=True,
                download_name='waitrose_vouchers.zip'
            )
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected: {e}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
