from pathlib import Path
import zipfile
folder=Path('data/tmp');folder.mkdir(exist_ok=True)
with zipfile.ZipFile(folder/'parser-test.docx','w') as z:
 z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
 z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
 z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Demonstration case: the next hearing is 17 November 2026. The client supplied a signed receipt.</w:t></w:r></w:p></w:body></w:document>')
# Minimal single-page PDF fixture, with correct object offsets.
parts=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
stream=b'BT /F1 12 Tf 72 720 Td (Demonstration PDF: filing deadline 20 November 2026.) Tj ET'
parts.append(b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream')
out=b'%PDF-1.4\n';offsets=[0]
for i,p in enumerate(parts,1):offsets.append(len(out));out+=f'{i} 0 obj\n'.encode()+p+b'\nendobj\n'
xref=len(out);out+=b'xref\n0 6\n0000000000 65535 f \n'+b''.join(f'{x:010} 00000 n \n'.encode() for x in offsets[1:])+f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode()
(folder/'parser-test.pdf').write_bytes(out)
