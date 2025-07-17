from fpdf import FPDF
from datetime import datetime

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Land Use Change Detection Report", ln=True, align="C")
        self.set_font("Arial", "", 10)
        self.cell(0, 10, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
        self.ln(10)

def generate_pdf_report(before_img_path, after_img_path, summary_data, chart_path, output_path, metadata, before_cluster_img_path, after_cluster_img_path):
    pdf = PDF()
    pdf.add_page()

    # Section 1: Project Info
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "1. Input Parameters", ln=True)
    pdf.set_font("Arial", "", 11)
    for key, val in metadata.items():
        pdf.cell(0, 8, f"{key}: {val}", ln=True)
    pdf.ln(5)

    # Section 2: Satellite Images
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "2. Before and After Imagery", ln=True)

    x_start = pdf.get_x()
    y_start = pdf.get_y()

    pdf.image(before_img_path, x=x_start, y=y_start, w=90)
    pdf.image(after_img_path, x=x_start + 100, y=y_start, w=90)

    # Move down to avoid overlap with next section
    pdf.set_y(y_start + 90)  # Adjust height based on your image size

    # Section 2.5: Classification Maps
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "2.5 Cluster Classification Maps", ln=True)

    x_start = pdf.get_x()
    y_start = pdf.get_y()

    # Draw images
    pdf.image(before_cluster_img_path, x=x_start, y=y_start, w=90)
    pdf.image(after_cluster_img_path, x=x_start + 100, y=y_start, w=90)

    # Move Y cursor manually BELOW the lowest image
    pdf.set_y(y_start + 65)  # This is usually enough based on w=90 image
    pdf.ln(10)  # Add a little extra vertical spacing if needed


    # Section 3: Summary Table
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "3. Change Detection Summary", ln=True)

    pdf.set_font("Arial", "", 10)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(30, 8, "Cluster", 1, 0, 'C', 1)
    pdf.cell(30, 8, "Before (ha)", 1, 0, 'C', 1)
    pdf.cell(30, 8, "After (ha)", 1, 0, 'C', 1)
    pdf.cell(30, 8, "Change", 1, 0, 'C', 1)
    pdf.cell(30, 8, "% Change", 1, 1, 'C', 1)

    for k in summary_data['clusters']:
        row = summary_data['clusters'][k]
        pdf.cell(30, 8, str(k), 1)
        pdf.cell(30, 8, str(row['before']), 1)
        pdf.cell(30, 8, str(row['after']), 1)
        pdf.cell(30, 8, str(row['change']), 1)
        pdf.cell(30, 8, str(row['percent']) + '%', 1, 1)

    pdf.ln(5)

    # Section 4: Chart
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "4. Area Comparison Chart", ln=True)
    pdf.image(chart_path, w=150)

    pdf.output(output_path)
