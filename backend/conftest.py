# -*- coding: utf-8 -*-
"""pytest 설정 — backend/ 를 sys.path에 넣어 `app...` import 가능하게."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
