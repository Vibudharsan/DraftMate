from pathlib import Path
p=Path('ai-workspace.js');s=p.read_text(encoding='utf-8-sig')
s=s.replace("function decorateAI(){const page=location.hash.slice(1);", "function decorateAI(){const page=location.hash.slice(1);const statusLabel=document.querySelector('#ai-provider-state');if(statusLabel)statusLabel.textContent=aiState.geminiConfigured?'Gemini configured · '+aiState.model:'Gemini not configured';")
s=s.replace("+contextBar()+`<div class=\"page-grid\">", "+`<section class=\"case-context compact-context\"><label>Use indexed documents from<select id=\"active-case\" aria-label=\"Case reference\">${caseOptions(activeCaseId)}</select></label><a class=\"source-link\" href=\"#casefile\">View case file ↗</a></section><div class=\"page-grid\">")
p.write_text(s,encoding='utf-8')
