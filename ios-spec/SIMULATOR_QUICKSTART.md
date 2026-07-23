# Indaga — живой цикл в iOS-симуляторе (Claude Code desktop)

## 0. Предусловия (один раз)
- **Mac на Apple Silicon** + установленный **Xcode** (из App Store), запустить его один раз → принять лицензию, доставить iOS Simulator runtime.
- **Claude Code desktop app** с включённой бетой «iOS Simulator» (та, что на скрине ClaudeDevs).
- `brew install xcodegen` (генерит `.xcodeproj` из `project.yml` — сам проект в gitignore).

## 1. Разовая настройка репозитория (в терминале на маке)
```bash
git clone https://github.com/indaga-ai/indaga-ios.git
cd indaga-ios
# девкит-онбординг (honesty-контракт, скрипты): см. indaga-ai/devkit → ONBOARDING.md + ./setup.sh
(cd IndagaKit && swift test)                 # ядро зелёное?
(cd IndagaApp && xcodegen generate)          # создаёт Indaga.xcodeproj
```

## 2. Проверка сборки (в терминале)
```bash
xcodebuild -scheme Indaga -sdk iphonesimulator -configuration Debug CODE_SIGNING_ALLOWED=NO build
```
Схема — **`Indaga`**, собирать через `-scheme`, не `-target`.

## 3. Первый промпт для Claude Code desktop (скопируй целиком)

> Собери и запусти приложение Indaga в iOS-симуляторе (iPhone 17 Pro, iOS 18.x).
> Проект — XcodeGen: сначала `cd IndagaApp && xcodegen generate`, затем собери схему `Indaga`
> (`xcodebuild -scheme Indaga -sdk iphonesimulator -configuration Debug CODE_SIGNING_ALLOWED=NO build`),
> установи и запусти через simctl, открой симулятор в панели.
>
> Затем прогони наш core loop как первый пользователь и на каждом шаге сними скриншот:
> 1. Онбординг: экран-приветствие тестера → **обязательный** экран согласия (галочка «I've read and agree…»,
>    кнопка Continue должна быть неактивна, пока не отмечено) → 3 вопроса квиза → «building» → summary → мост Apple Health.
> 2. Home (Vitality hub): убедись, что **сразу под vitality-кольцом** есть блок «Today's brief» (карточка морнинг-брифа)
>    и ссылка на Journal — выше teaser «Today's Read».
> 3. Открой морнинг-бриф, отметь одно действие, вернись — проверь, что стрик обновился.
> 4. Открой пейволл (после отчёта) — проверь цену и текст.
>
> ЧЕСТНОСТЬ (не нарушать, это продукт): чип уверенности берётся только из `chip(for:)`; при calibrating —
> «Calibrating n/14», при not_measured — «Unknown» (серый, никогда не зелёный); карточка брифа НИКОГДА не
> показывает hero-число. Если увидишь фейковую цифру, зелёный «грейд» или число вместо Unknown — это баг, стоп и покажи.
>
> Ничего не коммить без моего слова; сначала покажи скриншоты и что предлагаешь править.

## 4. Дальше — живой цикл
Правка SwiftUI → пересборка → Claude тыкает по экрану → скриншот → правит дизайн в реалтайме.
Ветка/PR/merge → Xcode Cloud → TestFlight остаётся прежним; симулятор — для итерации ДО мержа.

## Готчи
- `-sdk iphonesimulator` ок, пока не вмёржен виджет/watch (#62). После него — `-destination 'platform=iOS Simulator,name=iPhone 17 Pro'`.
- Если UI-тесты падают в 0.25с — обычно проблема установки бандла, а не логики; пусть Claude смотрит логи установки.
- Реальный Apple Health в симуляторе пустой → HealthKit-ветки покажут честный «Unknown»/пусто. Это правильно, не баг.
