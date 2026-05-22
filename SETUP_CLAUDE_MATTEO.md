# Setup Claude Code — BEPI (Matteo)

## 1. Hook git pull automatico

Apri `.claude/settings.json` nella cartella del progetto BEPI e aggiungi il blocco `"hooks"` come mostrato sotto.

Il file attuale probabilmente è così:

```json
{
  "model": "sonnet",
  ...altri campi...
}
```

Aggiungi `"hooks"` prima della `}` finale:

```json
{
  "model": "sonnet",
  ...altri campi...,
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "git -C /Users/matteo/Dev/BEPI pull --rebase --autostash 2>&1 | head -5"
          }
        ]
      }
    ]
  }
}
```

> **Nota**: cambia `/Users/matteo/Dev/BEPI` con il percorso reale della cartella BEPI sul tuo Mac.

Da quel momento Claude farà `git pull` automaticamente ogni volta che apri una sessione in questa cartella.

---

## 2. Workflow git (da seguire ogni sessione)

Claude lo sa già grazie al CLAUDE.md, ma per riferimento:

1. **Inizio sessione** → pull automatico (vedi sopra)
2. **Fai le modifiche** normalmente con Claude
3. **Fine sessione / feature pronta** → di' a Claude "committa e pusha" e lo fa lui

In caso di conflitti (Federico e tu avete toccato lo stesso file), Claude li risolve e poi committa.

---

## 3. Perché `.claude/settings.json` non è su git

Il file è in `.gitignore` — ogni Mac deve configurarlo separatamente. È normale.
