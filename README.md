# globals-in-loop-check

`globals-in-loop-check` détecte l'utilisation de variables globales à l'intérieur de boucles ou de compréhensions. Le projet est maintenant empaqueté en tant que bibliothèque Python avec une CLI, ce qui permet son intégration dans des hooks `pre-commit` ou des pipelines CI.

## Installation

```bash
pip install globals-in-loop-check
```

Pour un développement local :

```bash
pip install -e .[dev]
```

## Utilisation

Analysez un dossier ou une liste de fichiers :

```bash
globals-in-loop-check src/ package/module.py
```

Options utiles :

- `--short` : supprime le message d'aide.
- `--no-gitignore` : ignore les fichiers listés dans `.gitignore`.

### Intégration avec pre-commit

```yaml
repos:
  - repo: https://github.com/<votre_organisation>/<votre_projet>.git
    rev: v0.1.0
    hooks:
      - id: globals-in-loop-check
```

Ajoutez le fichier `.pre-commit-hooks.yaml` suivant à la racine du dépôt de votre
librairie (remplacez le dépôt ci-dessus par celui où sera publiée la release) :

```yaml
- id: globals-in-loop-check
  name: globals-in-loop-check
  entry: globals-in-loop-check
  language: python
  types: [python]
```

## Développement

Les tests sont basés sur `pytest` :

```bash
pytest
```

Une GitHub Action (`.github/workflows/release.yml`) exécute automatiquement les
tests et la construction du paquet lors de la publication d'une release.

## Licence

MIT
