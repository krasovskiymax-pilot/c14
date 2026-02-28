"""
Скрипт сборки ChatList с помощью PyInstaller.

Версия берётся из version.py. Имя исполняемого файла: ChatList-{version}.exe
"""
import subprocess
import sys
from pathlib import Path

import version


def _version_to_tuple(v: str) -> tuple[int, int, int, int]:
    """Преобразует '1.0.0' в (1, 0, 0, 0)."""
    parts = v.split(".")
    nums = [int(p) for p in parts[:4]]
    while len(nums) < 4:
        nums.append(0)
    return tuple(nums[:4])


def _write_version_file(path: Path) -> None:
    """Генерирует файл version info для Windows."""
    v = version.__version__
    vt = _version_to_tuple(v)
    content = f'''# UTF-8
# Сгенерировано build.py из version.py
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={tuple(vt)},
    prodvers={tuple(vt)},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(u'040904b0',
        [StringStruct(u'CompanyName', u'ChatList'),
        StringStruct(u'FileDescription', u'ChatList - сравнение ответов нейросетей'),
        StringStruct(u'FileVersion', u'{v}'),
        StringStruct(u'InternalName', u'ChatList'),
        StringStruct(u'LegalCopyright', u''),
        StringStruct(u'OriginalFilename', u'ChatList-{v}.exe'),
        StringStruct(u'ProductName', u'ChatList'),
        StringStruct(u'ProductVersion', u'{v}')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''
    path.write_text(content, encoding="utf-8")


def main() -> int:
    root = Path(__file__).parent
    version_str = version.__version__
    exe_name = f"ChatList-{version_str}"

    version_file = root / "version_info.txt"
    _write_version_file(version_file)
    print(f"Сборка ChatList {version_str} -> {exe_name}.exe")

    app_ico = root / "app.ico"
    extra = []
    if app_ico.exists():
        extra = ["--add-data", f"{app_ico};.", "--icon", str(app_ico)]

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--noconfirm",
        "--clean",
        f"--name={exe_name}",
        f"--version-file={version_file}",
        *extra,
        str(root / "main.py"),
    ]

    result = subprocess.run(cmd, cwd=root)
    version_file.unlink(missing_ok=True)  # удалить временный файл
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
