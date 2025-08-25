# PDF Form Mapping Sharing System

## Overview

The PDF Mapping Sharing System allows users to share their PDF form configurations with the community, making it easier for everyone to use common medical and prescription forms. When you map a PDF form's fields, you can share that mapping so others don't have to repeat the same work.

## How It Works

### For Users (Using Shared Mappings)

1. **Upload your PDF form** as usual
2. The system automatically checks if someone has already mapped this form
3. If a mapping exists, you'll see: **"✨ Community mapping available for this form!"**
4. Click **"Apply Community Mapping"** to instantly configure your form
5. Done! No manual mapping needed

### For Contributors (Sharing Your Mappings)

After you've successfully mapped a PDF form:

1. Click the **"Share with Community"** button
2. Choose privacy level:
   - **Anonymous**: Removes all personal information
   - **Credited**: Include your name as contributor (optional)
3. Add a brief description (e.g., "German prescription form 2024")
4. Click **"Generate Sharing Package"**
5. You'll get a simple email template with the mapping attached
6. Send it to: `mappings@medication-tracker.org` (or configured email)

That's it! No GitHub account needed, no technical knowledge required.

## Technical Implementation

### File Structure

Mappings are stored as JSON files in the repository:

```
medication-tracker/
├── app/
│   └── community-mappings/
│       ├── index.json           # Master index of all mappings
│       ├── verified/            # Officially verified mappings
│       │   └── [hash].json
│       └── contributed/         # Community contributions
│           └── [hash].json
```

### Mapping File Format

Each mapping is stored as a JSON file named by the PDF's SHA-256 hash:

```json
{
  "version": "1.0",
  "file_hash": "sha256:a3f5b8c2d4e6...",
  "metadata": {
    "original_filename": "prescription_form_2024.pdf",
    "form_name": "Standard Prescription Form",
    "publisher": "German Health Ministry",
    "form_version": "2024-01",
    "language": "de",
    "contributed_date": "2024-08-20",
    "contributor": "Anonymous",
    "verified": false,
    "usage_count": 0
  },
  "form_info": {
    "total_pages": 1,
    "field_count": 45,
    "rows_per_page": 16,
    "columns_count": 8
  },
  "mappings": {
    "structure_mapping": {
      "1_1": {"field": "patient_name", "row": 1, "col": 1},
      "1_2": {"field": "patient_dob", "row": 1, "col": 2},
      "2_1": {"field": "medication_name", "row": 2, "col": 1}
    },
    "content_mapping": {
      "column_formulas": {
        "1": {
          "fields": ["brand_name", "strength"],
          "separator": " "
        },
        "2": {
          "fields": ["daily_units", "dosage_form"],
          "separator": " "
        }
      }
    }
  },
  "checksum": "md5:1234567890abcdef"
}
```

### Database Schema

```sql
-- Community Mappings Table
CREATE TABLE community_mappings (
    id INTEGER PRIMARY KEY,
    file_hash VARCHAR(64) UNIQUE NOT NULL,
    original_filename VARCHAR(255),
    form_name VARCHAR(255),
    publisher VARCHAR(255),
    form_version VARCHAR(50),
    mapping_data JSON NOT NULL,
    contributor_name VARCHAR(100),
    contributed_date DATETIME,
    verified BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,
    last_used DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- PDF Templates Update
ALTER TABLE pdf_templates ADD COLUMN file_hash VARCHAR(64);
ALTER TABLE pdf_templates ADD COLUMN used_community_mapping BOOLEAN DEFAULT FALSE;
ALTER TABLE pdf_templates ADD COLUMN community_mapping_id INTEGER REFERENCES community_mappings(id);
```

### Implementation Phases

#### Phase 1: Core Functionality (Week 1)
- [x] Add SHA-256 hash calculation for PDFs
- [ ] Create database schema for community mappings
- [ ] Implement export mapping feature
- [ ] Create import/apply mapping functionality

#### Phase 2: Sharing System (Week 2)
- [ ] Add "Share with Community" button
- [ ] Create anonymization function
- [ ] Generate email template with attachment
- [ ] Set up receiving email system

#### Phase 3: Repository Integration (Week 3)
- [ ] Create GitHub workflow to process emails
- [ ] Auto-convert email attachments to JSON files
- [ ] Generate pull requests for new mappings
- [ ] Update master index

#### Phase 4: User Experience (Week 4)
- [ ] Auto-check for existing mappings on upload
- [ ] Preview mapping before applying
- [ ] Usage tracking and statistics
- [ ] Success notifications

### Privacy & Security

#### What Gets Shared
✅ **Included in mappings:**
- PDF structure information (field positions)
- Field mapping configuration
- Form metadata (name, publisher, version)
- Optional contributor name

❌ **Never included:**
- Patient data or personal health information
- Filled form content
- User account information
- Local file paths
- System information

#### Anonymization Process
When "Anonymous" is selected:
1. Remove contributor information
2. Strip custom field labels
3. Remove any user-specific configurations
4. Clear timestamp metadata
5. Generate clean mapping file

### Email Submission Process

For users without GitHub access, we provide a simple email-based submission:

1. System generates a `.json` mapping file
2. Creates pre-filled email template:
   ```
   To: mappings@medication-tracker.org
   Subject: [MAPPING] Form: [Form Name]
   
   Dear Medication Tracker Team,
   
   I would like to share my PDF form mapping with the community.
   
   Form Details:
   - Form Name: [Auto-filled]
   - Publisher: [Auto-filled]
   - Version: [Auto-filled]
   - File Hash: [Auto-filled]
   
   Please find the mapping file attached.
   
   Thank you for maintaining this community resource!
   
   [Optional: Your name for credits]
   ```
3. Automated system processes email:
   - Validates JSON structure
   - Checks for malicious content
   - Creates GitHub PR automatically
   - Sends confirmation email

### Benefits

#### For Individual Users
- **Time Saving**: Apply mappings in seconds instead of hours
- **Accuracy**: Use verified, tested mappings
- **No Technical Skills**: Simple one-click application
- **Offline Support**: Mappings cached locally

#### For Healthcare Providers
- **Standardization**: Consistent form handling across departments
- **Efficiency**: Reduce setup time for new installations
- **Compliance**: Use verified mappings for official forms
- **Updates**: Automatic notifications for form updates

#### For the Community
- **Collaboration**: Users helping users
- **Growing Library**: More forms supported over time
- **Quality**: Popular mappings get verified
- **Accessibility**: No barriers to contribution

### Future Enhancements

#### Version 2.0
- Mapping versioning for form updates
- Conflict resolution for multiple mappings
- Rating and review system
- Automatic form detection

#### Version 3.0
- AI-assisted mapping suggestions
- Multi-language form support
- Publisher verification program
- Mapping marketplace for complex forms

### API Endpoints

```python
# Check for existing mapping
GET /api/pdf-mapper/check-mapping/<file_hash>

# Download community mapping
GET /api/pdf-mapper/community-mapping/<file_hash>

# Export current mapping
POST /api/pdf-mapper/export/<template_id>

# Submit mapping (generates email)
POST /api/pdf-mapper/submit-mapping/<template_id>

# Apply community mapping
POST /api/pdf-mapper/apply-mapping/<template_id>
```

### Configuration

Add to `app/config.py`:

```python
# Community Mapping Settings
COMMUNITY_MAPPINGS_ENABLED = True
MAPPINGS_SUBMISSION_EMAIL = 'mappings@medication-tracker.org'
MAPPINGS_CACHE_DIR = 'app/community-mappings'
MAPPINGS_CACHE_TTL = 604800  # 7 days in seconds
MAPPINGS_AUTO_CHECK = True
MAPPINGS_REPO_URL = 'https://github.com/medication-tracker/community-mappings'
```

### Success Metrics

- Number of mappings shared
- Number of mappings applied
- Time saved (estimated)
- User satisfaction ratings
- Form coverage percentage

### Getting Started

For developers who want to implement this system:

1. **Add hash calculation** to PDF upload process
2. **Create database tables** using provided schema
3. **Implement export feature** in PDF mapper
4. **Set up email processing** (can use AWS SES, SendGrid, etc.)
5. **Create GitHub workflow** for automated PR creation
6. **Add import/matching** logic
7. **Test with common forms** in your region

### Questions & Support

For questions about implementing this system:
- Open an issue on GitHub
- Contact the development team
- Check the implementation guide

For users wanting to share mappings:
- Use the in-app sharing feature
- Email mappings@medication-tracker.org
- No technical knowledge required!