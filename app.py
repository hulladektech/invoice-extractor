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
        "Invoice No", "Buyer's Details", "Description of Goods / Services", "HSN / SAC",
        "Qty", "Alt Qty", "Rate", "Disc (Amt.)", "Total Value", "Taxable Value"
    ])

    with pdfplumber.open(file) as pdf:
        invoice_no = ""
        buyer_details = ""

        for page in pdf.pages:
            text = page.extract_text()

            if not text:
                continue

            # Invoice Number
            inv_match = re.search(r'Invoice No\s*:\s*(ABL\/IN\/\d+\/FY\d+)', text)
            if inv_match:
                invoice_no = inv_match.group(1).strip()

            # FIXED Buyer’s Name Extraction (based on actual PDF structure)
            buyer_details = ""
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if "Buyer's Details" in line:
                    if i + 1 < len(lines):
                        # Usually Buyer | Shipping on one line, split at double-space
                        parts = re.split(r'\s{2,}', lines[i + 1])
                        if parts:
                            buyer_details = parts[0].strip()
                    break



            # Extract item rows using pattern
            item_pattern = re.findall(
                r'(\d+)\s+([A-Za-z0-9\-\(\) \/]+?)\s+(\d{8})\s+(\d+)\s+([A-Za-z]*)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})',
                text
            )

            for item in item_pattern:
                sl_no, desc, hsn, qty, alt_qty, rate, disc, total_value, taxable_value = item
                writer.writerow([
                    invoice_no,
                    buyer_details,
                    desc.strip(),
                    hsn.strip(),
                    qty.strip(),
                    alt_qty.strip(),
                    rate.strip(),
                    disc.strip(),
                    total_value.strip(),
                    taxable_value.strip()
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
