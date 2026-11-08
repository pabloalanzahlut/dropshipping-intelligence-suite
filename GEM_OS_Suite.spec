# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('app/database/dropshipping_suite.db', 'data_template'), ('data/config.json', 'data_template'), ('data/youtube_channels.json', 'data_template'), ('data/queue_state.json', 'data_template'), ('.env', '.'), ('ai_workspace', 'ai_workspace'), ('app/ui/resources', 'app/ui/resources'), ('app/templates', 'app/templates'), ('app/static', 'app/static'), ('data', 'data')]
binaries = []
hiddenimports = ['app.services.transcript_store', 'app.services.topic_filter', 'app.services.agent_router', 'app.services.channel_store', 'app.services.kb_maintenance', 'app.services.product_catalog', 'app.services.business_metrics', 'app.services.exports', 'app.services.log_viewer', 'app.services.web_auth', 'uvicorn', 'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto', 'fastapi', 'fastapi.routing', 'fastapi.openapi', 'starlette', 'starlette.routing', 'pydantic', 'pydantic.json', 'pydantic.types', 'youtube_transcript_api', 'yt_dlp', 'dotenv', 'markdown', 'requests', 'openai', 'apscheduler', 'apscheduler.schedulers.background', 'apscheduler.triggers.interval', 'tkinter', 'tkinter.ttk', 'tkinter.scrolledtext', 'xml.etree.ElementTree']
tmp_ret = collect_all('app.services')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('app.ui.components')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('app.database')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('app.utils')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['app/main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GEM_OS_Suite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GEM_OS_Suite',
)
