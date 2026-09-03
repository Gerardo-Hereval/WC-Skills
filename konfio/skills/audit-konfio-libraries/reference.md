# Reference — `@konfio/*` inventory

Supporting material for [SKILL.md](SKILL.md).

## Package roles (one line each)

| Package                  | Role in inventory                                          |
| ------------------------ | ---------------------------------------------------------- |
| `@konfio/base`           | Legacy atoms — **list each imported module**               |
| `@konfio/components`     | Legacy molecules/organisms — **list each imported module** |
| `@konfio/forms`          | Legacy forms — list field components / hooks               |
| `@konfio/icons`          | Peer — summarize `Icon` vs named icons                     |
| `@konfio/design-tokens`  | CSS only — list `@import` paths                            |
| `@konfio/design-system`  | Published NDS — list adopted modules if any                |
| `@konfio/kamila-chatbot` | Widget — usually one export                                |

Labels (legacy / peer / tokens / widget) go in the summary table only — no long taxonomy prose in chat output.

---

## Import path normalization

Collapse to **component key** for grouping:

| Raw import path                                                       | Inventory key                      |
| --------------------------------------------------------------------- | ---------------------------------- |
| `@konfio/base/button`                                                 | `button`                           |
| `@konfio/base/ui/atoms/button/button`                                 | `button`                           |
| `@konfio/components/molecules/dialog`                                 | `dialog`                           |
| `@konfio/components/ui/molecules/status-disclaimer/status-disclaimer` | `status-disclaimer`                |
| `@konfio/forms/...`                                                   | last path segment or forms subpath |
| `@konfio/icons` + `{ CloseIcon }`                                     | named: `CloseIcon`                 |
| `@konfio/icons` + `{ Icon }`                                          | generic: `Icon`                    |
| `@konfio/design-system/ui/atoms/button`                               | `ui/atoms/button`                  |

Count **import statements** per file (one line = one import).

---

## Grep cheatsheet

```bash
# Library totals
rg -o "from ['\"]@konfio/[a-z0-9-]+" apps/<app> --glob '!**/node_modules/**' \
  | sed "s/.*@konfio\\///;s/['\"]//" | sort | uniq -c | sort -rn

# Components — base
rg -o "from ['\"]@konfio/base/[a-z0-9/-]+" apps/<app> \
  | sed "s/.*@konfio\\///;s/['\"]//" | sort | uniq -c | sort -rn

# Components — components package
rg -o "from ['\"]@konfio/components/[a-z0-9/-]+" apps/<app> \
  | sed "s/.*@konfio\\///;s/['\"]//" | sort | uniq -c | sort -rn

# Forms
rg -o "from ['\"]@konfio/forms/[a-z0-9/-]+" apps/<app> \
  | sed "s/.*@konfio\\///;s/['\"]//" | sort | uniq -c | sort -rn

# Design-system (NDS)
rg -o "from ['\"]@konfio/design-system/[a-z0-9/-]+" apps/<app> \
  | sed "s/.*@konfio\\///;s/['\"]//" | sort | uniq -c | sort -rn

# CSS
rg -n "@konfio/" apps/<app> --glob '*.css'

# Catalog versions
rg "'@konfio/" pnpm-workspace.yaml

# Monorepo legacy totals by app
for d in apps/*/; do
  b=$(rg -c "from ['\"]@konfio/base" "$d" 2>/dev/null | awk -F: '{s+=$2} END {print s+0}')
  c=$(rg -c "from ['\"]@konfio/components" "$d" 2>/dev/null | awk -F: '{s+=$2} END {print s+0}')
  f=$(rg -c "from ['\"]@konfio/forms" "$d" 2>/dev/null | awk -F: '{s+=$2} END {print s+0}')
  t=$((b+c+f))
  [ "$t" -gt 0 ] && echo "$t $d (base:$b components:$c forms:$f)"
done | sort -rn
```

---

## Related skills

| Skill                          | When                              |
| ------------------------------ | --------------------------------- |
| `audit-konfio-libraries`       | This skill — inventory only       |
| `migrate-konfio-design-system` | kui → konfio migration + API diff |

After inventory, user may ask for remediation — that is **not** part of this skill unless explicitly requested.
