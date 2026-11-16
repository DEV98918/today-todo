"""cPanel「Setup Python App」(Passenger) 入口文件。

在 cPanel 创建应用时：
  Application root        = 本文件所在目录
  Application startup file = passenger_wsgi.py
  Application entry point  = application
"""
import os
import sys

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

# Passenger 约定：模块级变量名为 application 的 WSGI  callable
from server import app as application  # noqa: E402
