# Translation Management Commands

Quick reference for all translation management commands in the Medication Tracker project.

## 🚀 Main Command (Recommended)

```bash
./scripts/manage-grouped-translations.sh <command> [options]
```

### **Available Commands:**

| Command | Description | Example |
|---------|-------------|---------|
| `extract` | Extract translatable strings into domain-specific .pot files | `./scripts/manage-grouped-translations.sh extract` |
| `init` | Initialize .po files for all domains and languages | `./scripts/manage-grouped-translations.sh init -l de` |
| `update` | Update existing .po files with new strings from .pot files | `./scripts/manage-grouped-translations.sh update` |
| `compile` | Compile .po files to .mo files for all domains and languages | `./scripts/manage-grouped-translations.sh compile` |
| `upload` | Upload domain-specific .pot files to Crowdin | `./scripts/manage-grouped-translations.sh upload` |
| `download` | Download translated .po files from Crowdin | `./scripts/manage-grouped-translations.sh download` |
| `glossary` | Upload medical/technical glossary to Crowdin | `./scripts/manage-grouped-translations.sh glossary` |
| `status` | Show translation coverage for all domains and languages | `./scripts/manage-grouped-translations.sh status` |
| `full` | Run complete workflow: extract → init → compile | `./scripts/manage-grouped-translations.sh full` |

### **Options:**

| Option | Description | Example |
|--------|-------------|---------|
| `-l, --lang LANG` | Process only specific language | `-l de` (German only) |
| `-d, --domain DOM` | Process only specific domain | `-d core` (Core UI only) |
| `-h, --help` | Show help message | `--help` |

---

## 📚 Glossary Management

### **Automated Upload (Recommended):**
```bash
# Upload 26 medical/technical terms to Crowdin
./scripts/manage-grouped-translations.sh glossary

# Or use dedicated script
./scripts/upload-glossary.sh
```

### **Manual Upload (Fallback):**
If CLI upload fails, use these files in Crowdin web interface:
- `crowdin-glossary.csv` - CSV format with headers
- `crowdin-glossary.json` - JSON format (original)

---

## 🔧 Legacy Scripts (Updated for Domain System)

### **Crowdin Initialization:**
```bash
./scripts/crowdin-prime.sh    # Full setup: extract → upload → glossary
```

### **Status Monitoring:**
```bash
./scripts/crowdin-status.sh           # Quick Crowdin project status
./scripts/translation-coverage.sh     # Legacy coverage (shows migration info)
```

---

## 🎯 Common Workflows

### **1. First-Time Setup:**
```bash
# Extract strings into domains
./scripts/manage-grouped-translations.sh extract

# Initialize languages  
./scripts/manage-grouped-translations.sh init -l de
./scripts/manage-grouped-translations.sh init -l es
./scripts/manage-grouped-translations.sh init -l fr

# Upload to Crowdin
./scripts/manage-grouped-translations.sh upload

# Upload glossary
./scripts/manage-grouped-translations.sh glossary
```

### **2. Development Workflow:**
```bash
# After adding new translatable strings
./scripts/manage-grouped-translations.sh extract
./scripts/manage-grouped-translations.sh update
./scripts/manage-grouped-translations.sh upload
```

### **3. Translation Update:**
```bash
# Get latest translations from Crowdin
./scripts/manage-grouped-translations.sh download
./scripts/manage-grouped-translations.sh compile

# Check progress
./scripts/manage-grouped-translations.sh status
```

### **4. Quick Everything:**
```bash
# Complete development workflow
./scripts/manage-grouped-translations.sh full
```

---

## 🌍 Domain Structure

The translation system organizes strings into **9 logical domains**:

| Domain | Strings | Content |
|--------|---------|---------|
| **core** | 38 | Navigation, layout, dashboard, common UI |
| **medications** | 5 | Medication management and details |
| **inventory** | 3 | Stock management and tracking |
| **orders** | 16 | Prescription ordering and fulfillment |
| **physicians** | 9 | Doctor management and information |
| **visits** | 7 | Appointment scheduling and planning |
| **schedules** | 7 | Medication scheduling and timing |
| **settings** | 53 | System configuration and preferences |
| **prescriptions** | 10 | Prescription templates and management |

**Total: 148 strings** across all domains

---

## ⚙️ Prerequisites

### **Required Tools:**
```bash
# Crowdin CLI
npm install -g @crowdin/cli
# OR
brew install crowdin

# Python for glossary conversion
python3 --version
```

### **Environment Setup:**
Create `.env` file with:
```
CROWDIN_PROJECT_ID=your_project_id
CROWDIN_API_TOKEN=your_api_token
```

---

## 🔍 Troubleshooting

### **Common Issues:**

1. **"Crowdin CLI not found"**
   ```bash
   npm install -g @crowdin/cli
   ```

2. **"Missing Crowdin credentials"**
   - Check `.env` file exists
   - Verify `CROWDIN_PROJECT_ID` and `CROWDIN_API_TOKEN` are set

3. **"Domain files not found"**
   ```bash
   ./scripts/manage-grouped-translations.sh extract
   ```

4. **"Glossary upload failed"**
   - Check API token permissions
   - Try manual upload via Crowdin web interface

---

## 📊 Monitoring

### **Check Status:**
```bash
# Domain-based coverage
./scripts/manage-grouped-translations.sh status

# Crowdin project status  
./scripts/crowdin-status.sh

# Application translation debug
curl http://localhost:8087/debug/translation-coverage
```

---

**🎉 The system is ready for professional translation management with domain-based organization and automated glossary support!**