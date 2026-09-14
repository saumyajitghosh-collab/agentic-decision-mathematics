import pathlib

p = pathlib.Path('static/js/app.js')
t = p.read_bytes().decode('utf-8', errors='surrogateescape')

t = t.replace('alarm" : ""`)`}', 'alarm" : ""})`}')
t = t.replace('mathrm{cap_k', 'mathrm{cap}_k')
t = t.replace('mathrm{AUTO(a)', 'mathrm{AUTO}(a)')
t = t.replace('mathrm{Safe(a)', 'mathrm{Safe}(a)')
t = t.replace(',Ua)', ',U)}')

q, sq = chr(34), chr(39)
old9 = '>": "&gt;", ' + sq + q + sq + ': "&#39;"'
new9 = '>": "&gt;", ' + sq + q + sq + ': "&quot;", ' + sq + q + sq + ': "&#39;"'
if old9 in t:
    t = t.replace(old9, new9)

p.write_bytes(t.encode('utf-8', errors='surrogateescape'))
print('fixes applied')
