"""
Regenera PLAN.pdf a partir de PLAN.md.

    py -3.11 tools_md2pdf.py            # PLAN.md -> PLAN.pdf
    py -3.11 tools_md2pdf.py otro.md    # otro.md -> otro.pdf

Requiere:  pip install markdown       (Edge ya viene con Windows 11)
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile

try:
    import markdown
except ImportError:
    sys.exit("Falta la libreria 'markdown'.  Instalala con:  py -3.11 -m pip install markdown")

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

CSS = """
@page { size: A4; margin: 16mm 15mm 16mm 15mm; }
* { box-sizing: border-box; }
body {
  font-family: "Segoe UI", "Inter", system-ui, sans-serif;
  font-size: 10pt; line-height: 1.55; color: #1a1d21; margin: 0;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
h1 { font-size: 23pt; font-weight: 700; letter-spacing: -0.02em; color: #0b1220;
     margin: 0 0 4mm 0; padding-bottom: 3mm; border-bottom: 2.5pt solid #0e7c86; }
h2 { font-size: 14pt; font-weight: 700; color: #0e7c86; margin: 9mm 0 3mm 0;
     padding-bottom: 1.5mm; border-bottom: 0.6pt solid #cfd8dc;
     break-after: avoid; page-break-after: avoid; }
h3 { font-size: 11.5pt; font-weight: 650; color: #14303a; margin: 6mm 0 2mm 0;
     break-after: avoid; page-break-after: avoid; }
h1 + p, h2 + p, h3 + p, h2 + table, h3 + table { break-before: avoid; page-break-before: avoid; }
p { margin: 0 0 2.6mm 0; orphans: 3; widows: 3; }

table { width: 100%; border-collapse: collapse; margin: 3mm 0 4mm 0;
        font-size: 8.6pt; line-height: 1.4; }
thead { display: table-header-group; }
tr { break-inside: avoid; page-break-inside: avoid; }
th { background: #0e7c86; color: #fff; font-weight: 650; text-align: left;
     padding: 1.8mm 2.2mm; border: 0.4pt solid #0e7c86; vertical-align: bottom; }
td { padding: 1.6mm 2.2mm; border: 0.4pt solid #d4dde0; vertical-align: top; }
tbody tr:nth-child(even) td { background: #f4f8f9; }

code { font-family: Consolas, "Cascadia Mono", monospace; font-size: 0.88em;
       background: #eef2f4; color: #0b3d45; padding: 0.3mm 1mm; border-radius: 1.2mm; }
th code { background: rgba(255,255,255,0.22); color: #fff; }
pre { font-family: Consolas, "Cascadia Mono", monospace; background: #f7f9fa;
      border: 0.4pt solid #d4dde0; border-left: 2pt solid #0e7c86; border-radius: 1.5mm;
      padding: 2.5mm 3mm; margin: 3mm 0 4mm 0; font-size: 7.4pt; line-height: 1.22;
      white-space: pre; overflow: visible; break-inside: avoid; page-break-inside: avoid; }
pre code { background: none; color: #14303a; padding: 0; font-size: inherit; white-space: pre; }

blockquote { margin: 3mm 0; padding: 2.2mm 3.5mm; background: #fff8e6;
             border-left: 2.5pt solid #d99b1c; border-radius: 0 1.5mm 1.5mm 0;
             break-inside: avoid; page-break-inside: avoid; }
blockquote p { margin: 0 0 1.5mm 0; }
blockquote p:last-child { margin-bottom: 0; }

ul, ol { margin: 0 0 3mm 0; padding-left: 5.5mm; }
li { margin-bottom: 1.2mm; }
li > ul, li > ol { margin-top: 1.2mm; }
hr { border: none; border-top: 0.5pt solid #dde4e7; margin: 6mm 0; }
strong { font-weight: 650; color: #0b1220; }
a { color: #0e7c86; text-decoration: none; }
"""


def find_edge() -> str:
    for path in EDGE_CANDIDATES:
        if pathlib.Path(path).exists():
            return path
    sys.exit("No encontre msedge.exe. Edita EDGE_CANDIDATES con la ruta correcta.")


def main() -> None:
    src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "PLAN.md").resolve()
    if not src.exists():
        sys.exit(f"No existe: {src}")
    dst = src.with_suffix(".pdf")

    body = markdown.markdown(
        src.read_text(encoding="utf-8"),
        extensions=["tables", "fenced_code", "sane_lists", "attr_list"],
        output_format="html5",
    )
    html = (
        '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">'
        f"<title>{src.stem}</title><style>{CSS}</style></head><body>{body}</body></html>"
    )

    # Edge necesita una ruta sin espacios para el file:// y un perfil propio en headless.
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        html_file = tmp_path / "doc.html"
        pdf_file = tmp_path / "doc.pdf"
        html_file.write_text(html, encoding="utf-8")

        subprocess.run(
            [
                find_edge(),
                "--headless=new",
                "--disable-gpu",
                f"--user-data-dir={tmp_path / 'profile'}",
                "--no-pdf-header-footer",
                f"--print-to-pdf={pdf_file}",
                html_file.as_uri(),
            ],
            check=True,
            capture_output=True,
        )

        if not pdf_file.exists():
            sys.exit("Edge no genero el PDF.")
        shutil.copy(pdf_file, dst)

    print(f"OK  {src.name} -> {dst.name}  ({dst.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
