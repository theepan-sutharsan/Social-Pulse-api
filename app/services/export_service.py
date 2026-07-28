from app.utils.csv_utils import rows_to_csv_response
from app.utils.pdf_utils import table_pdf_response

class ExportService:
    @staticmethod
    def export_csv(filename, headers, rows):
        return rows_to_csv_response(filename, headers, rows)

    @staticmethod
    def export_pdf(filename, title, headers, rows):
        return table_pdf_response(filename, title, headers, rows)
