# Excel Template Workflow

This document explains how to upload, catalogue, and retrieve Excel templates using the new `/api/v1/excel-templates` endpoints.

## Overview

- Templates are stored under `app/static/uploads/excel-templates/`.
- Metadata (sheet names, named ranges, sample headers, workbook properties) is captured and stored in the `excel_templates` table.
- Files are restricted to `.xlsx` and `.xlsm` formats with a maximum size of 10&nbsp;MB.
- Each template exposes a `download_url` (`/api/v1/excel-templates/{id}/download`) that returns the original filename and content type.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/v1/excel-templates/upload` | Upload a new template (multipart form-data). |
| `GET` | `/api/v1/excel-templates/` | List catalogued templates (metadata + download URL). |
| `GET` | `/api/v1/excel-templates/{id}` | Retrieve metadata for a single template. |
| `GET` | `/api/v1/excel-templates/{id}/download` | Download the stored workbook. |
| `DELETE` | `/api/v1/excel-templates/{id}` | Remove the workbook and its metadata. |

## Upload Example

```bash
curl -X POST "http://localhost:8010/api/v1/excel-templates/upload" \
  -H "accept: application/json" \
  -F "file=@templates/SampleInvoice.xlsx" \
  -F "name=Sample Invoice" \
  -F "category=invoices" \
  -F "description=Invoice layout with line-item breakdown"
```

Response excerpt:

```json
{
  "id": "3fd8117f-5f0e-4e46-99d6-52ca32bf5c77",
  "name": "Sample Invoice",
  "public_url": "/static/uploads/excel-templates/excel_template_....xlsx",
  "download_url": "/api/v1/excel-templates/3fd8117f-5f0e-4e46-99d6-52ca32bf5c77/download",
  "workbook_metadata": {
    "sheet_names": ["Invoice"],
    "named_ranges": [],
    "sample_headers": {
      "Invoice": ["Item", "Qty", "Price", "Total"]
    },
    "document_properties": {
      "creator": "Finance",
      "created": "2024-08-12T10:45:00"
    }
  }
}
```

## Integration Tips

- Use `sheet_names` and `sample_headers` to map dynamic fields from your UI into the workbook.
- Preserve `download_url` in the front-end so users can fetch the original template when needed.
- Consider extending the service with versioning or ownership metadata once authentication is wired in.

## Next Steps & Enhancements

- **Client-side editing:** Evaluate spreadsheet components (SpreadJS, Handsontable, Syncfusion) for in-browser editing of uploaded workbooks.
- **Template versioning:** Track revisions and allow rollbacks.
- **Data binding:** Define placeholder syntax (e.g., `${customer.name}`) and inject runtime data when generating new spreadsheets.
- **Access control:** Restrict upload/delete actions to authorized roles once authentication middleware is enforced.
