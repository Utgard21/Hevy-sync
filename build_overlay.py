from pathlib import Path

root = Path('/app')
app_path = root / 'app.py'
index_path = root / 'static' / 'index.html'

app = app_path.read_text(encoding='utf-8')
old_e1rm = "item['best_weight']=max(old_weight,best); item['e1rm']=max(old_e1rm,best_e1rm);"
new_e1rm = "item['best_weight']=max(old_weight,best); item['e1rm']=max(old_e1rm,best_e1rm,item['best_weight']);"
if old_e1rm in app:
    app = app.replace(old_e1rm, new_e1rm, 1)
elif new_e1rm not in app:
    raise RuntimeError('Could not locate e1RM assignment to patch')

old_static = "'/sw.js':'sw.js'}"
new_static = "'/sw.js':'sw.js','/polish.js':'polish.js','/polish.css':'polish.css'}"
if old_static in app:
    app = app.replace(old_static, new_static, 1)
elif new_static not in app:
    raise RuntimeError('Could not locate static file map to patch')
app_path.write_text(app, encoding='utf-8')

index = index_path.read_text(encoding='utf-8')
if '/polish.css' not in index:
    if '</head>' not in index:
        raise RuntimeError('Could not locate </head> in index.html')
    index = index.replace('</head>', '<link rel="stylesheet" href="/polish.css"></head>', 1)
if '/polish.js' not in index:
    if '</body>' not in index:
        raise RuntimeError('Could not locate </body> in index.html')
    index = index.replace('</body>', '<script src="/polish.js"></script></body>', 1)
index_path.write_text(index, encoding='utf-8')
