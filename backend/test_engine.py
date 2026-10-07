# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
from engine.engine import run_engine

def on_event(e):
    ts = e.get('ts', '')
    t = e.get('type', '')
    msg = e.get('msg', e.get('chars', ''))
    print(f"[{ts}] {t}: {msg}", flush=True)

run_engine('汉末神机-我携灵算定三分', 3, on_event, None, 2)
print('DONE', flush=True)
