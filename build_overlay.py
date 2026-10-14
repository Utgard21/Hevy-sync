from pathlib import Path

root = Path('/app')
app_path = root / 'app.py'
index_path = root / 'static' / 'index.html'
ui_path = root / 'static' / 'app.js'


def patch_once(source, old, new, label):
    if old in source:
        return source.replace(old, new, 1)
    if new not in source:
        raise RuntimeError(f'Could not locate {label} to patch')
    return source


app = app_path.read_text(encoding='utf-8')

app = patch_once(
    app,
    "item['best_weight']=max(old_weight,best); item['e1rm']=max(old_e1rm,best_e1rm);",
    "item['best_weight']=max(old_weight,best); item['e1rm']=max(old_e1rm,best_e1rm,item['best_weight']);",
    'e1RM assignment',
)

# Keep the timeline compact, but expose the exact event count separately so
# monthly reports never mistake the 30-event payload cap for the real total.
app = patch_once(
    app,
    "'load':load,'prs':sorted(prs,key=lambda x:x['date'],reverse=True)[:30]}",
    "'load':load,'pr_count':len(prs),'prs':sorted(prs,key=lambda x:x['date'],reverse=True)[:30]}",
    'PR count response',
)

# Manual measurements can override every metric that the Hevy importer stores,
# including side-specific measurements. Imported values themselves remain read-only.
old_manual_metrics = "if metric not in ('weight','waist','chest','hips','biceps','thigh','neck','shoulders','calf'): raise ValueError('Unknown measurement')"
new_manual_metrics = "if metric not in ('weight','waist','chest','hips','biceps','thigh','neck','shoulders','calf','left_biceps','right_biceps','left_thigh','right_thigh','left_calf','right_calf','left_forearm','right_forearm','lean_mass','body_fat','abdomen'): raise ValueError('Unknown measurement')"
app = patch_once(app, old_manual_metrics, new_manual_metrics, 'manual measurement metric whitelist')

app = patch_once(
    app,
    "'/sw.js':'sw.js'}",
    "'/sw.js':'sw.js','/polish.js':'polish.js','/polish.css':'polish.css'}",
    'static file map',
)
app_path.write_text(app, encoding='utf-8')

# rep_prs stores the best recorded load at an exact repetition count. Calling
# those values "8RM", "10RM", etc. implies a true repetition maximum, which
# the recorded workout data does not establish. Label the chips literally.
ui = ui_path.read_text(encoding='utf-8')
ui = patch_once(
    ui,
    "r+'RM · '+num(w)+' kg'",
    "'Best '+r+'-rep set · '+num(w)+' kg'",
    'exact-rep record chip label',
)
ui_path.write_text(ui, encoding='utf-8')

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