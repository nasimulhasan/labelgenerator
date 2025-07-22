from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
import pandas as pd
from fpdf import FPDF
import os, zipfile, re, html
from PyPDF2 import PdfMerger

app = Flask(__name__, template_folder="templates")

UPLOAD_FOLDER = "uploads"
LABEL_FOLDER = "labels"
FONT_NAME = "CustomFont"
FONT_FILE = "Mango Dream.ttf"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LABEL_FOLDER, exist_ok=True)


def title_case(text):
    return str(text).strip().title()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload_header_footer", methods=["POST"])
def upload_header_footer():
    header = request.files.get("header")
    footer = request.files.get("footer")
    header_path = footer_path = ""

    if header:
        header_path = os.path.join(UPLOAD_FOLDER, secure_filename(header.filename))
        header.save(header_path)

    if footer:
        footer_path = os.path.join(UPLOAD_FOLDER, secure_filename(footer.filename))
        footer.save(footer_path)

    return jsonify({"header_path": header_path, "footer_path": footer_path})


@app.route("/upload_excel", methods=["POST"])
def upload_excel():
    file = request.files.get("excel_file")
    if file:
        filepath = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
        file.save(filepath)
        df = pd.read_excel(filepath)
        df["Invoice"] = df["Invoice"].ffill()
        invoices = sorted(df["Invoice"].dropna().astype(str).unique().tolist())
        return jsonify({"invoices": invoices, "path": filepath})
    return jsonify({"error": "No file uploaded"}), 400


@app.route("/generate_excel_labels", methods=["POST"])
def generate_excel_labels():
    data = request.json
    file_path = data["file_path"]
    start_invoice = data["start_invoice"]
    end_invoice = data["end_invoice"]
    header_file = data.get("header_file", "")
    footer_file = data.get("footer_file", "")

    df = pd.read_excel(file_path)
    for col in ["Invoice", "First Name", "Last Name", "Phone", "Address", "Order Total Amount", "Note"]:
        df[col] = df[col].ffill()

    invoice_list = sorted(df["Invoice"].dropna().astype(str).unique().tolist())
    start_idx = invoice_list.index(start_invoice)
    end_idx = invoice_list.index(end_invoice)
    invoice_range = invoice_list[start_idx:end_idx + 1]

    class PDF(FPDF):
        def __init__(self):
            super().__init__("P", "mm", (101.6, 152.4))
            self.add_font(FONT_NAME, "", FONT_FILE, uni=True)
            self.set_font(FONT_NAME, "", 10)

        def header(self):
            if header_file and os.path.exists(header_file):
                self.image(header_file, x=0, y=0, w=101.6, h=30.0)

        def footer(self):
            if footer_file and os.path.exists(footer_file):
                self.image(footer_file, x=0, y=106.4, w=101.6, h=49.0)

        def label_content(self, row):
            self.set_xy(5, 41)
            label_width, value_width, line_height = 17, 66, 5

            self.cell(label_width, line_height, "Invoice #:", 0)
            self.cell(value_width, line_height, row["Invoice Number"], 0, ln=True)
            self.ln(2)

            self.cell(label_width, line_height, "Name:", 0)
            self.cell(value_width, line_height, row["Customer Name"], 0, ln=True)
            self.ln(2)

            self.cell(label_width, line_height, "Phone:", 0)
            self.cell(value_width, line_height, row["Phone Number"], 0, ln=True)
            self.ln(2)

            self.cell(label_width, line_height, "Address:", 0)
            self.multi_cell(value_width, line_height, row["Shipping Address"], 0)
            self.ln(2)

            self.set_x(5)
            self.cell(label_width, line_height, "Total:", 0)
            self.cell(value_width, line_height, f"Tk {row['Total Amount']}", 0, ln=True)
            self.ln(2)

            self.set_x(5)
            self.cell(91, line_height, "Items:", ln=True)
            self.ln(1)

            for item in row["Item List"].split(";"):
                self.set_x(5)
                self.cell(150, line_height, f"- {item.strip()}", ln=True)

    pdf_files = []
    for invoice, group in df.groupby("Invoice"):
        invoice_str = str(invoice).strip()
        if invoice_str not in invoice_range:
            continue

        valid_items = []
        for _, item_row in group.iterrows():
            name = item_row.get("Items")
            qty = item_row.get("Quantity")
            if pd.isna(name) or str(name).strip() == "":
                continue
            cleaned = title_case(html.unescape(re.sub(r"[\n\r]+", " ", str(name))))
            qty_str = f" ({int(qty)})" if not pd.isna(qty) else ""
            valid_items.append(f"{cleaned}{qty_str}")

        if not valid_items:
            continue

        first_row = group.iloc[0]
        phone = str(first_row["Phone"]).split(".")[0]
        if not phone.startswith("0"):
            phone = "0" + phone

        note = str(first_row.get("Note", "")).strip().lower()
        is_paid = "paid" in note
        amount = "0" if is_paid else str(int(float(first_row["Order Total Amount"])))

        label = {
            "Invoice Number": invoice_str,
            "Customer Name": title_case(f"{first_row['First Name']} {first_row['Last Name']}"),
            "Phone Number": phone,
            "Shipping Address": title_case(first_row["Address"]),
            "Total Amount": amount,
            "Item List": "; ".join(valid_items)
        }

        pdf = PDF()
        pdf.set_auto_page_break(False)
        pdf.set_margins(5, 5, 5)
        pdf.add_page()
        pdf.label_content(label)

        filename = f"{LABEL_FOLDER}/{invoice_str.replace('/', '-')}.pdf"
        pdf.output(filename)
        pdf_files.append(filename)

    merged = os.path.join(LABEL_FOLDER, "merged_labels.pdf")
    merger = PdfMerger()
    for f in pdf_files:
        merger.append(f)
    merger.write(merged)
    merger.close()

    zip_path = "shipping_labels_all.zip"
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for f in pdf_files:
            zipf.write(f, os.path.basename(f))
        zipf.write(merged, "merged_labels.pdf")

    return send_file(zip_path, as_attachment=True)

if __name__ == "__main__":
    app.run()
