# Documentation

This directory contains the documentation for fastapi_otel_common, built with [Jekyll](https://jekyllrb.com/) and the [Just the Docs](https://just-the-docs.github.io/just-the-docs/) theme.

## 📚 Documentation Structure

- `index.md` - Home page and overview
- `installation.md` - Installation guide
- `configuration.md` - Configuration reference
- `middleware.md` - Middleware documentation
- `security.md` - Security and authentication
- `database.md` - Database integration
- `examples.md` - Working examples
- `contributing.md` - Contributing guidelines

## 🚀 Building Locally

### Prerequisites

- Ruby 3.2+
- Bundler

### Setup

```bash
# Install dependencies
cd docs
bundle install

# Serve locally
bundle exec jekyll serve

# Visit http://localhost:4000
```

### Building

```bash
bundle exec jekyll build
```

The built site will be in `_site/`.

## 🌐 GitHub Pages Deployment

The documentation is automatically deployed to GitHub Pages when changes are pushed to the `main` branch.

### Setup GitHub Pages

1. Go to your repository settings
2. Navigate to "Pages" section
3. Set Source to "GitHub Actions"
4. The `.github/workflows/pages.yml` workflow will handle deployment

## 📝 Writing Documentation

### Front Matter

Each page should have Jekyll front matter:

```yaml
---
layout: default
title: Page Title
nav_order: 1
---
```

### Navigation

- `nav_order` determines the order in the sidebar
- Lower numbers appear first
- Use table of contents for long pages

### Code Blocks

Use fenced code blocks with language identifiers:

````markdown
```python
from fastapi_otel_common import create_app

app = create_app()
```
````

### Links

Use relative links for internal pages:

```markdown
[Configuration Guide](configuration.md)
```

## 🎨 Theme Customization

The theme is configured in `_config.yml`. Key settings:

- `theme: just-the-docs` - Using Just the Docs theme
- `color_scheme: dark` - Dark mode by default
- `search_enabled: true` - Full-text search enabled
- Back to top links enabled
- GitHub edit links enabled

## 📦 Files

- `_config.yml` - Jekyll configuration
- `Gemfile` - Ruby dependencies
- `*.md` - Documentation pages

## 🔗 Useful Links

- [Just the Docs Documentation](https://just-the-docs.github.io/just-the-docs/)
- [Jekyll Documentation](https://jekyllrb.com/docs/)
- [GitHub Pages Documentation](https://docs.github.com/en/pages)
