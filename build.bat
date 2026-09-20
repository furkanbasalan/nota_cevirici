@echo off
REM Yerel derleme: Python 3.10+ ve Inno Setup 6 kurulu olmalı.
python -m pip install -r requirements.txt || exit /b 1
python -m unittest discover -s tests || exit /b 1
pyinstaller --noconfirm --windowed --name NotaCevirici --paths src --collect-all verovio main.py || exit /b 1
"%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" installer.iss || exit /b 1
echo.
echo Kurulum dosyasi: installer_output\NotaCevirici-Kurulum.exe
