import base64
import io
from pathlib import Path
from typing import Union

import fitz  # PyMuPDF


def pdf_to_base64_images(
    pdf_source: Union[str, Path, bytes],
    dpi: int = 150,
    image_format: str = "PNG",
) -> list[str]:
    """Convert each page of a PDF to a base64-encoded image string.

    Args:
        pdf_source: File path (str/Path) or raw PDF bytes.
        dpi: Resolution for rendering. 150 is a good balance of quality vs size.
        image_format: Output image format — "PNG" or "JPEG".

    Returns:
        List of base64 strings (one per page), without data-URI prefix.
    """
    if isinstance(pdf_source, (str, Path)):
        doc = fitz.open(str(pdf_source))
    else:
        doc = fitz.open(stream=pdf_source, filetype="pdf")

    zoom = dpi / 72  # 72 is the default PDF DPI
    matrix = fitz.Matrix(zoom, zoom)
    fmt = image_format.upper()

    results: list[str] = []
    try:
        for page in doc:
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img_bytes = pix.tobytes(output=fmt.lower())
            results.append(base64.b64encode(img_bytes).decode("utf-8"))
    finally:
        doc.close()

    return results


def base64_pdf_to_base64_images(
    base64_pdf: str,
    dpi: int = 150,
    image_format: str = "PNG",
) -> list[str]:
    """Convert a base64-encoded PDF string to a list of base64 image strings.

    Decodes the PDF from base64, renders each page, and returns one base64
    image string per page.
    """
    padded = base64_pdf + "=" * (-len(base64_pdf) % 4)
    pdf_bytes = base64.b64decode(padded)
    return pdf_to_base64_images(pdf_bytes, dpi=dpi, image_format=image_format)


def pdf_to_base64_data_uris(
    pdf_source: Union[str, Path, bytes],
    dpi: int = 150,
    image_format: str = "PNG",
) -> list[str]:
    """Same as pdf_to_base64_images but returns full data URIs.

    Useful for embedding directly in HTML or passing to vision models that
    expect ``data:image/png;base64,<data>`` format.
    """
    mime = "image/png" if image_format.upper() == "PNG" else "image/jpeg"
    return [
        f"data:{mime};base64,{b64}"
        for b64 in pdf_to_base64_images(pdf_source, dpi=dpi, image_format=image_format)
    ]