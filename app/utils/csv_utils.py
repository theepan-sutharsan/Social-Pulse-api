"""
Social Pulse API — CSV Utilities
Uses stdlib csv + io — no extra dependencies.
"""
import csv
import io
from flask import Response


def rows_to_csv_response(filename: str, headers: list, rows: list) -> Response:
    """
    Build an in-memory CSV and return it as a Flask attachment response.

    :param filename: Filename for the Content-Disposition header (e.g. 'videos-2026-07-28.csv')
    :param headers: List of column names (first row of CSV)
    :param rows: List of lists/tuples representing data rows
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    csv_data = output.getvalue()
    output.close()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def parse_csv_file(file_storage, required_columns: list):
    """
    Parse an uploaded werkzeug FileStorage CSV file.

    :param file_storage: werkzeug FileStorage object
    :param required_columns: list of column names that must be present in the header
    :returns: (rows: list[dict], errors: list[str])
              rows is empty and errors is populated if header validation fails.
    """
    try:
        raw = file_storage.read().decode("utf-8-sig")  # handles BOM
    except Exception as e:
        return [], [f"Failed to read file: {str(e)}"]

    reader = csv.DictReader(io.StringIO(raw))
    fieldnames = reader.fieldnames or []
    missing = [col for col in required_columns if col not in fieldnames]
    if missing:
        return [], [f"Missing required columns: {', '.join(missing)}"]

    rows = []
    for row in reader:
        rows.append(dict(row))

    return rows, []
