# Multi-Language Support with Crowdin

This document provides comprehensive instructions for managing the multi-language support system in the Medication Tracker application using Flask-Babel and Crowdin.

## 📊 Current Status

### ✅ Fully Implemented:
- **Flask-Babel 4.0.0** integration with modern locale selector API
- **714 translatable strings** extracted from all templates and Python files  
- **1,100+ translation markers** across the entire application
- **Automatic language detection** (URL → session → browser → fallback)
- **Docker integration** with proper translation file deployment
- **Quality controls** - only languages with >80% completion shown in UI

### 🌍 Language Support:
- **English (en)** - Base language (100%)
- **German (de)** - Testing implementation (~1% complete)
- **Spanish (es)** - Ready for translation (0%)
- **French (fr)** - Ready for translation (0%)

---

## 🚀 Getting Started

### Prerequisites
```bash
# Install Crowdin CLI (one-time setup)
brew install crowdin
# OR
npm install -g @crowdin/cli
```

### Initial Crowdin Setup

1. **Create Crowdin Project:**
   - Go to [crowdin.com](https://crowdin.com)
   - Create new project: "Medication Tracker"
   - Select source language: English
   - Add target languages: German, Spanish, French

2. **Configure Project Settings:**
   - File format: GNU Gettext (.po/.pot)
   - Quality assurance: Enable all checks
   - Workflow: Simple (or use approval workflow for production)

3. **Get API Credentials:**
   - Project Settings → API → Generate new token
   - Copy Project ID and API token
   - Update `crowdin.yml` with your credentials:
   ```yaml
   project_id: "your-project-id"
   api_token: "your-api-token"
   ```

4. **Initial Upload:**
   ```bash
   # Upload source template with 714 strings
   crowdin upload sources
   ```

---

## 🔄 Daily Workflow

### For Developers (Adding New Features)

#### 1. Mark New Strings for Translation
**Templates (`*.html`):**
```html
<!-- Static text -->
<h1>{{ _('New Feature Name') }}</h1>
<p>{{ _('Feature description text') }}</p>

<!-- Text with variables -->
<span>{{ _('Hello, %(name)s!', name=user.name) }}</span>
```

**Python files (`*.py`):**
```python
from flask_babel import gettext as _

# Flash messages
flash(_('Operation completed successfully!'), 'success')
flash(_('Error: {}').format(error_message), 'error')

# Form validation
if not data:
    return _('This field is required')
```

#### 2. Extract New Strings
```bash
# Extract all translatable strings
cd app && pybabel extract -F ../babel.cfg -k _ -o ../translations/messages.pot .
```

#### 3. Update Translation Files
```bash
# Update existing language files with new strings
pybabel update -i translations/messages.pot -d translations
```

#### 4. Upload to Crowdin
```bash
# Upload new strings for translation
crowdin upload sources
```

#### 5. Download Completed Translations (Weekly/Monthly)
```bash
# Download latest translations from Crowdin
crowdin download

# Compile binary files for production
pybabel compile -d translations
```

### For Translators

#### Using Crowdin Web Interface:
1. **Access Project:** [your-crowdin-project-url]
2. **Select Language:** Choose your target language
3. **Translate Strings:** Use Crowdin's intuitive web editor
4. **Features Available:**
   - Translation Memory (reuse previous translations)
   - Machine Translation suggestions
   - Context screenshots
   - Comments and discussions
   - Quality assurance checks
   - Glossary and terminology management

#### Translation Guidelines:
- **Medical Terminology:** Use established medical translations
- **UI Consistency:** Keep button/menu text concise
- **Context Matters:** Consider where text appears (button vs. description)
- **Variables:** Don't translate placeholder variables like `%(name)s`

---

## 🔧 Advanced Configuration

### Language Coverage Threshold (80% Rule)

The application automatically hides languages with <80% translation coverage from the navigation bar:

```python
# In app/main.py - get_available_languages function
def get_available_languages():
    """Return only languages with >80% translation coverage"""
    available = {}
    
    for code, name in app.config['LANGUAGES'].items():
        if code == 'en':  # Always show English
            available[code] = name
            continue
            
        coverage = calculate_translation_coverage(code)
        if coverage >= 0.8:  # 80% threshold
            available[code] = name
    
    return available
```

### Calculating Translation Coverage:
```bash
# Check completion status for a language
msgfmt --statistics translations/de/LC_MESSAGES/messages.po
# Output: 142 translated messages, 572 untranslated messages.
# Coverage: 142/714 = 19.9%
```

### Automated Quality Checks:
```bash
# Check for translation errors
pybabel check translations/de/LC_MESSAGES/messages.po

# Validate compiled files
python -c "
import babel.messages.pofile as po
catalog = po.read_po(open('translations/de/LC_MESSAGES/messages.po'))
print(f'Translation coverage: {len([m for m in catalog if m.string])/len(catalog)*100:.1f}%')
"
```

---

## 🔄 CI/CD Integration

### GitHub Actions Workflow

Create `.github/workflows/translations.yml`:
```yaml
name: Translation Sync
on:
  push:
    branches: [main, development]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  sync-translations:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: |
          pip install babel flask-babel
          npm install -g @crowdin/cli
      
      - name: Extract strings
        run: |
          cd app && pybabel extract -F ../babel.cfg -k _ -o ../translations/messages.pot .
      
      - name: Upload to Crowdin
        run: crowdin upload sources
        env:
          CROWDIN_TOKEN: ${{ secrets.CROWDIN_TOKEN }}
      
      - name: Download from Crowdin
        run: crowdin download
        env:
          CROWDIN_TOKEN: ${{ secrets.CROWDIN_TOKEN }}
      
      - name: Compile translations
        run: pybabel compile -d translations
      
      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add translations/
          git diff --staged --quiet || git commit -m "chore: update translations"
          git push
```

---

## 🐳 Docker Integration

### Build Process
The Docker build automatically includes all translation files:
```dockerfile
# Copy translation files
COPY translations/ ./translations/

# Compile translations during build
RUN pybabel compile -d translations
```

### Environment Variables
```bash
# Set default language for container
ENV FLASK_DEFAULT_LANGUAGE=en

# Override in docker-compose
environment:
  - FLASK_DEFAULT_LANGUAGE=de
```

---

## 🧪 Testing Translations

### Local Testing
```bash
# Test specific language
curl "http://localhost:8087/?lang=de"

# Test language switching
curl -b "session=..." "http://localhost:8087/set_language/es"
```

### Translation Validation
```bash
# Check for missing translations
grep -c "msgstr \"\"" translations/de/LC_MESSAGES/messages.po

# Validate all languages
for lang in de es fr; do
  echo "=== $lang ==="
  msgfmt --statistics translations/$lang/LC_MESSAGES/messages.po 2>&1
done
```

### UI Testing
- **Layout Testing:** Verify UI accommodates longer translations (German, Spanish)
- **Character Encoding:** Test special characters (ä, ö, ü, ñ, é, etc.)
- **Context Testing:** Ensure translations make sense in context
- **Mobile Testing:** Verify responsive design with different text lengths

---

## 🔍 Troubleshooting

### Common Issues

**1. Translations not loading:**
```bash
# Check if .mo files exist
ls -la translations/*/LC_MESSAGES/messages.mo

# Recompile translations
pybabel compile -d translations

# Restart application
```

**2. New strings not appearing in Crowdin:**
```bash
# Re-extract strings
cd app && pybabel extract -F ../babel.cfg -k _ -o ../translations/messages.pot .

# Check template file
grep -A5 -B5 "your new string" translations/messages.pot

# Upload to Crowdin
crowdin upload sources --verbose
```

**3. Language not showing in navigation:**
```bash
# Check coverage (needs >80%)
python -c "
import babel.messages.pofile as po
catalog = po.read_po(open('translations/de/LC_MESSAGES/messages.po'))
translated = len([m for m in catalog if m.string])
total = len(catalog)
print(f'Coverage: {translated}/{total} = {translated/total*100:.1f}%')
"
```

### Debug Mode
Enable translation debugging by setting:
```python
# In app/main.py
app.config['DEBUG_TRANSLATIONS'] = True
```

---

## 📈 Translation Progress Tracking

### Coverage Statistics
```bash
# Generate coverage report for all languages
./scripts/translation-coverage.sh
```

Create `scripts/translation-coverage.sh`:
```bash
#!/bin/bash
echo "Translation Coverage Report"
echo "=========================="
for lang_dir in translations/*/LC_MESSAGES; do
  lang=$(basename $(dirname $lang_dir))
  if [[ $lang != "en" ]]; then
    echo -n "$lang: "
    msgfmt --statistics $lang_dir/messages.po 2>&1 | grep -o '[0-9]* translated' | cut -d' ' -f1
  fi
done | awk '{total=714; printf "%-3s: %3d/714 (%5.1f%%)\n", $1, $2, ($2/total)*100}'
```

### Quality Metrics
- **Translation Accuracy:** Manual review + community feedback
- **Consistency:** Glossary usage and translation memory
- **Completeness:** Coverage tracking and automated reminders
- **Localization:** Cultural adaptation beyond literal translation

---

## 🎯 Production Deployment

### Release Checklist
- [ ] Extract latest strings (`pybabel extract`)
- [ ] Upload to Crowdin (`crowdin upload sources`)
- [ ] Wait for translation completion (>80% coverage)
- [ ] Download translations (`crowdin download`)
- [ ] Compile translations (`pybabel compile`)
- [ ] Test all active languages
- [ ] Deploy with Docker build
- [ ] Verify language switching in production

### Monitoring
- **Translation Coverage:** Track completion percentages
- **Error Monitoring:** Watch for missing translation errors
- **User Feedback:** Monitor language preference usage
- **Performance:** Check translation loading times

---

## 📞 Support

### For Translation Issues:
- Check this documentation
- Review Crowdin project activity
- Test locally with `?lang=XX` parameter
- Check server logs for Babel errors

### For Technical Issues:
- Verify Flask-Babel configuration
- Check translation file compilation
- Validate Docker translation inclusion
- Review CI/CD pipeline logs

### Resources:
- **Flask-Babel Documentation:** https://python-babel.github.io/flask-babel/
- **Crowdin Documentation:** https://support.crowdin.com/
- **GNU Gettext Manual:** https://www.gnu.org/software/gettext/manual/

---

**Last Updated:** August 13, 2025  
**Translation Template Version:** 714 strings  
**Supported Languages:** English, German, Spanish, French