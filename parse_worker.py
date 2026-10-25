"""Bounded child process for local document conversion; never accepts remote URLs."""
from pathlib import Path
from markitdown import MarkItDown
import sys
p=Path(sys.argv[1]);result=MarkItDown(enable_plugins=False).convert(str(p)).text_content
if len(result)>1_000_000:raise ValueError('Extracted text too large')
p.with_suffix('.parsed.txt').write_text(result,encoding='utf-8')
