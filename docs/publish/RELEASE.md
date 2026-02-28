# Публикация ChatList на GitHub Release и GitHub Pages

## Подготовка

Убедитесь, что:
- Python 3.11+ установлен
- Виртуальное окружение создано и активировано
- Inno Setup 6 установлен
- Все зависимости установлены: `pip install -r requirements.txt`

---

## Шаг 1. Обновление версии

1. Откройте `version.py`
2. Измените `__version__` на новую версию (например, `"1.0.1"`)
3. Закоммитьте: `git add version.py && git commit -m "Версия 1.0.1"`

---

## Шаг 2. Сборка и публикация

### Вариант A: Автоматически (GitHub Actions)

1. Обновите версию в `version.py` и закоммитьте
2. Создайте и запушьте тег:
   ```powershell
   git tag v1.0.0
   git push origin v1.0.0
   ```
3. Workflow сам соберёт установщик и создаст Release на GitHub

### Вариант B: Вручную

```powershell
cd D:\Work\c14
.\venv\Scripts\Activate.ps1
python build_installer.py
```

Результат: `installer\ChatList-1.0.0-setup.exe` (имя зависит от версии).

---

## Шаг 3. Создание GitHub Release (при ручной сборке)

### 3.1. Через веб-интерфейс

1. Откройте репозиторий на GitHub
2. Справа нажмите **Releases** → **Create a new release**
3. **Choose a tag**: создайте тег, например `v1.0.0` (формат: `v` + версия)
4. **Release title**: `ChatList 1.0.0` или `Версия 1.0.0`
5. **Describe this release**: вставьте текст из шаблона ниже
6. В блоке **Attach binaries** перетащите `ChatList-1.0.0-setup.exe` из папки `installer\`
7. Нажмите **Publish release**

### 3.2. Через GitHub CLI (опционально)

```powershell
# Установка: winget install GitHub.cli
gh auth login
gh release create v1.0.0 installer\ChatList-1.0.0-setup.exe --title "ChatList 1.0.0" --notes "Выпуск 1.0.0"
```

---

## Шаг 4. Включение GitHub Pages

1. В репозитории: **Settings** → **Pages**
2. **Source**: GitHub Actions
3. Workflow **Deploy GitHub Pages** будет запускаться при пуше в `docs/` или вручную

Либо старый способ: **Deploy from a branch** → ветка `main`, папка `/docs`

Лендинг: `https://<username>.github.io/<repo-name>/`

---

## Шаг 5. Обновление лендинга при новом релизе

1. Откройте `docs/index.html`
2. Обновите ссылку на последний установщик и версию в секции «Скачать»
3. При необходимости обновите changelog
4. Закоммитьте и запушьте изменения

---

## Шаблон описания релиза

```markdown
## ChatList 1.0.0

Сравнение ответов нейросетей — отправка одного промта в несколько моделей ИИ (OpenAI, Claude, Llama и др. через OpenRouter).

### Установка

Скачайте `ChatList-1.0.0-setup.exe` и запустите установщик.

### Требования

- Windows 10/11 (64-bit)
- Файл `.env` с API-ключами (см. `.env.example`)

### Изменения в этой версии

- Первый публичный релиз
```

---

## Checklist перед релизом

- [ ] Версия обновлена в `version.py`
- [ ] `python build_installer.py` выполнен успешно
- [ ] Установщик проверен на чистой системе
- [ ] README актуален
- [ ] `.env.example` присутствует и документирован
