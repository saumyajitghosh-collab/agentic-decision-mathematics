import pathlib

p = pathlib.Path('static/js/app.js')
t = p.read_text()
t = t.replace('AUTOM(a)', 'AUTO(a)')
t = t.replace('Safet(a)', 'Safe(a)')
t = t.replace('bi/]', 'big]')
t = t.replace('cap_k`', 'cap_k}`')
t = t.replace('alarm" : ""`)`}', 'alarm" : ""})`}')
p.write_text(t)

p = pathlib.Path('static/css/app.css')
t = p.read_text()
t = t.replace('produce it', 'produced it')
t = t.replace('border-left:  3px', 'border-left: 3px')
t = t.replace('/* --------- lattice', '/* ---------- lattice')
t = t.replace('padding: 8px 10px;\nborder-radius', 'padding: 8px 10px; border-radius')
if '.tag.warn' not in t:
    t = t.replace('.tag { display: inline-block;', '.tag.warn { background: #fbe9e7; color: var(--deny); }\n.tag { display: inline-block;', 1)
p.write_text(t)
print('fixes applied')
