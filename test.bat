@echo off
set PYTHONPATH=%~dp0
python -m unittest discover -s tests
pause
