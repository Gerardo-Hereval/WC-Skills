# Inventory output template — `@konfio/*` libraries

Chat only. Keep compact.

---

## Single app

```markdown
## `@konfio/*` inventory — `apps/<app>`

| Library                | Version | Imports | Files | Role   |
| ---------------------- | ------- | ------: | ----: | ------ |
| @konfio/components     | 0.10.0  |   **6** |     6 | legacy |
| @konfio/base           | 0.4.5   |       3 |     3 | legacy |
| @konfio/icons          | 0.6.1   |       5 |     5 | peer   |
| @konfio/kamila-chatbot | 2.6.0   |       1 |     1 | widget |
| @konfio/design-tokens  | 0.3.0   |       — | 1 css | tokens |
| @konfio/design-system  | —       |       0 |     0 | —      |

**Legacy total:** 9 imports · 8 files

### `@konfio/components`

| Component                       | Imports | Files |
| ------------------------------- | ------: | ----: |
| **dialog** (`molecules/dialog`) |       6 |     6 |

### `@konfio/base`

| Component                         | Imports | Files |
| --------------------------------- | ------: | ----: |
| progress-indicator                |       1 |     1 |
| button (`ui/atoms/button/button`) |       1 |     1 |
| logo                              |       1 |     1 |

### `@konfio/icons`

| Usage                                                    | Imports | Files |
| -------------------------------------------------------- | ------: | ----: |
| `Icon` (generic)                                         |       3 |     3 |
| Named (`HideIcon`, `ShowIcon`, `LockIcon`, `UnlockIcon`) |       2 |     2 |

### `@konfio/kamila-chatbot`

| Component      | Imports | Files |
| -------------- | ------: | ----: |
| `KamilaWidget` |       1 |     1 |

### CSS — `@konfio/design-tokens`

- `globals.css`: safelist, design-system-export

**Overlap:** 4 files mix legacy `@konfio/*` with `@kui/design-system` (optional one line)
```

---

## Monorepo

```markdown
## `@konfio/*` inventory — monorepo

| App   | base | components | forms | icons |  ds | legacy imports |
| ----- | ---: | ---------: | ----: | ----: | --: | -------------: |
| cards |   84 |         42 |    12 |    55 |   0 |            138 |
| home  |    3 |          6 |     0 |     5 |   0 |              9 |
| …     |      |            |       |       |     |                |

### Detail — apps with legacy imports only

(per-app component tables, same shape as single app)
```

---

## Empty / clean app

```markdown
## `@konfio/*` inventory — `apps/<app>`

No `@konfio/base|components|forms` imports. Peers only: icons (N), design-tokens (CSS).
```

---

## Expansion (only if user asks)

- Full call-site list for one component
- Declared-but-unused deps
- Overlap file names

Do not include these by default.
