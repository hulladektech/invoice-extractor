from flask import Flask, request, send_file, render_template
import pdfplumber
import csv
import io
import re

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['pdf_file']
    if not file or not file.filename.endswith('.pdf'):
        return "Invalid file format. Please upload a PDF file.", 400

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Invoice No", "Invoice Date", "Buyer Name",
        "Full Description", "Battery Voltage", "Battery Capacity",
        "HSN / SAC", "Qty", "Alt Qty", "Rate",
        "Disc (Amt.)", "Total Value", "Taxable Value"
    ])

    with pdfplumber.open(file) as pdf:
        invoice_no = ""
        invoice_date = ""
        buyer_name = ""

        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            lines = text.split('\n')

            # Extract Invoice No
            inv_match = re.search(r'Invoice No\s*:\s*([A-Z0-9\/\-]+)', text)
            if inv_match:
                invoice_no = inv_match.group(1).strip()

            # Extract Invoice Date
            date_match = re.search(r'Invoice Date\s*:\s*(\d{2}-\d{2}-\d{4})', text)
            if date_match:
                invoice_date = date_match.group(1).strip()

            # Extract Buyer Name
            for i, line in enumerate(lines):
                if "Buyer's Details" in line and i + 1 < len(lines):
                    buyer_name = lines[i + 1].strip().split("  ")[0]
                    break

            # Extract item lines using a strong regex pattern
            for line in lines:
                item_match = re.match(
                    r'^(\d+)\s+(.*?)\s+(\d{8})\s+(\d+)\s+([A-Za-z]+)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})',
                    line
                )
                if item_match:
                    sl_no = item_match.group(1)
                    full_desc = item_match.group(2).strip()
                    hsn = item_match.group(3)
                    qty = item_match.group(4)
                    alt_qty = item_match.group(5)
                    rate = item_match.group(6)
                    disc = item_match.group(7)
                    total_value = item_match.group(8)
                    taxable_value = item_match.group(9)

                    # Normalize description to extract voltage and capacity
                    desc_norm = full_desc.lower().replace(",", "").replace("amps", "amp")

                    battery_voltage = ""
                    battery_capacity = ""

                    volt_match = re.search(r'(\d+(?:\.\d+)?)\s*v', desc_norm, re.IGNORECASE)
                    if volt_match:
                        battery_voltage = volt_match.group(1) + "V"

                    cap_match = re.search(r'(\d+(?:\.\d+)?)\s*(ah|amp|A)', desc_norm, re.IGNORECASE)
                    if cap_match:
                        battery_capacity = cap_match.group(1) + cap_match.group(2).capitalize()

                    writer.writerow([
                        invoice_no, invoice_date, buyer_name,
                        full_desc, battery_voltage, battery_capacity,
                        hsn, qty, alt_qty, rate, disc, total_value, taxable_value
                    ])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='extracted_invoice_data.csv'
    )

if __name__ == '__main__':
    app.run(debug=True)
