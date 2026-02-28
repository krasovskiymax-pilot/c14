"""
Скрипт сборки установщика ChatList с помощью Inno Setup.

Версия берётся из version.py. Сначала собирается exe (build.py), затем создаётся
установщик ChatList-{version}-setup.exe в папке installer/.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import version


def _find_iscc() -> Path | None:
    """Ищет компилятор Inno Setup (iscc.exe)."""
    # Стандартная установка в Program Files
    for base in [
        Path(r"C:\Program Files (x86)\Inno Setup 6"),
        Path(r"C:\Program Files\Inno Setup 6"),
    ]:
        iscc = base / "ISCC.exe"
        if iscc.exists():
            return iscc
    # Реестр Windows (InstallLocation)
    try:
        import winreg
        for hkey, subkey in [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1"),
        ]:
            try:
                with winreg.OpenKey(hkey, subkey) as key:
                    path, _ = winreg.QueryValueEx(key, "InstallLocation")
                    if path:
                        iscc = Path(path) / "ISCC.exe"
                        if iscc.exists():
                            return iscc
            except OSError:
                pass
    except ImportError:
        pass
    # В PATH
    found = shutil.which("iscc") or shutil.which("ISCC.exe")
    if found:
        return Path(found)
    return None


def main() -> int:
    root = Path(__file__).parent
    version_str = version.__version__
    exe_name = f"ChatList-{version_str}"
    exe_path = root / "dist" / f"{exe_name}.exe"

    # 1. Собрать exe, если ещё нет
    if not exe_path.exists():
        print("Сборка исполняемого файла...")
        result = subprocess.run(
            [sys.executable, str(root / "build.py")],
            cwd=root,
        )
        if result.returncode != 0:
            print("Ошибка: сборка exe не удалась.")
            return result.returncode
    else:
        print(f"Найден: {exe_path}")

    # 2. Найти Inno Setup
    iscc = _find_iscc()
    if not iscc:
        print(
            "Ошибка: Inno Setup не найден. Установите Inno Setup 6:\n"
            "  https://jrsoftware.org/isinfo.php"
        )
        return 1

    # 3. Сгенерировать ChatList.iss из шаблона
    iss_template = root / "ChatList.iss.in"
    iss_path = root / "ChatList.iss"
    if not iss_template.exists():
        print("Ошибка: не найден ChatList.iss.in")
        return 1
    iss_content = iss_template.read_text(encoding="utf-8").replace("{{VERSION}}", version_str)
    iss_path.write_text(iss_content, encoding="utf-8")

    # 4. Собрать установщик
    (root / "installer").mkdir(exist_ok=True)
    cmd = [str(iscc), str(iss_path)]
    print(f"Сборка установщика ChatList-{version_str}-setup.exe...")
    result = subprocess.run(cmd, cwd=root)
    if result.returncode != 0:
        return result.returncode

    out_file = root / "installer" / f"ChatList-{version_str}-setup.exe"
    if out_file.exists():
        print(f"Готово: {out_file}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
