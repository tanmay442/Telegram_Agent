import os
import datetime

try:
    import docx2pdf
except ImportError:  # pragma: no cover - optional dependency
    docx2pdf = None


def _build_output_path(output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_converted.pdf"
    return os.path.join(output_dir, filename)


def convert_docx_to_pdf(input_path: str, output_dir: str) -> str:
    if docx2pdf is None:
        raise RuntimeError("docx2pdf is not installed. Install it to convert DOCX files.")
    output_path = _build_output_path(output_dir)
    docx2pdf.convert(input_path, output_path)
    return output_path


def convert_pptx_to_pdf(input_path: str, output_dir: str) -> str:
    raise NotImplementedError("PPTX to PDF conversion is not supported in this Linux build.")


def convert_xlsx_to_pdf(input_path: str, output_dir: str) -> str:
    raise NotImplementedError("XLSX to PDF conversion is not supported in this Linux build.")


def office_to_pdf(input_path: str, output_dir: str) -> str:
    ext = os.path.splitext(input_path)[1].lower()
    if ext == ".docx":
        return convert_docx_to_pdf(input_path, output_dir)
    if ext == ".pptx":
        return convert_pptx_to_pdf(input_path, output_dir)
    if ext == ".xlsx":
        return convert_xlsx_to_pdf(input_path, output_dir)
    raise ValueError("Unsupported file format")
