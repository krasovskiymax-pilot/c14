# Документация и лендинг ChatList

- **index.html** — лендинг для GitHub Pages
- **publish/** — инструкции и шаблоны для публикации

## Настройка лендинга перед первой публикацией

1. Откройте `index.html` и замените:
   - `USER` — ваш GitHub username
   - `REPO` — имя репозитория (например, `c14`)
   - Версию `1.0.0` на актуальную

2. Либо выполните:
   ```powershell
   cd docs\publish
   .\update-landing.ps1 -Version "1.0.0" -User "yourusername" -Repo "c14"
   ```

## GitHub Pages

В настройках репозитория: **Settings → Pages → Source**: ветка `main`, папка `/docs`.
