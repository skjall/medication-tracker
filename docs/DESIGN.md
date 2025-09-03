# Design Guidelines

This document defines the visual design system and styling guidelines for the Medication Tracker application.

## Core Design Principles

### 1. **Consistency Over Variety**
- Use a limited, well-defined color palette
- Avoid "color disease" - excessive use of different colors without purpose
- Maintain consistent spacing, typography, and component styling across all views

### 2. **Semantic Color Usage**
Colors should have specific meaning and be used consistently throughout the application.

### 3. **Accessibility First**
- Ensure sufficient color contrast
- Don't rely solely on color to convey information
- Use icons and text labels alongside color coding

## Color System

### Primary Colors

#### **Primary Blue (`btn-primary`, `bg-primary`)**
- **Usage**: Default color for all actions, buttons, and card headers
- **When to use**: 
  - Main action buttons (Save, Create, Edit, Submit)
  - Secondary action buttons (View Details, Manage, Configure)
  - Card headers for information sections
  - Status badges for normal states
  - Navigation elements
- **Examples**: "Add Package", "Edit Product", "Save Settings", card headers

#### **Danger Red (`btn-danger`, `bg-danger`, `alert-danger`)**
- **Usage**: ONLY for dangerous/destructive actions
- **When to use**:
  - Delete buttons
  - Critical error alerts
  - "Out of stock" warnings
  - Actions that cannot be undone
- **Examples**: "Delete Product", "Remove Prescription", critical system errors

#### **Warning Orange (`alert-warning`, `bg-warning`)**
- **Usage**: Pre-alert state, caution, important notices
- **When to use**:
  - Low stock warnings ("Medications will run out before next visit")
  - Upcoming expiry dates (within 30 days)
  - Configuration warnings
  - Migration notices
- **Examples**: "Low inventory warning", "Package expires soon", "Requires attention"

### Secondary Colors

#### **Muted Gray (`text-muted`, `bg-light`)**
- **Usage**: Secondary information, disabled states
- **When to use**:
  - Helper text and descriptions
  - Timestamps and metadata
  - Disabled form elements
  - Secondary navigation

#### **White/Light (`bg-white`, `bg-light`)**
- **Usage**: Card backgrounds, form backgrounds, clean sections

### Colors to AVOID

❌ **Do NOT use these Bootstrap classes:**
- `btn-success`, `bg-success` (except for specific semantic indicators like "Allowed/Not Allowed")
- `btn-info`, `bg-info` 
- `btn-secondary`, `bg-secondary`
- `text-success`, `text-info`, `text-warning` (for general text)

## Component Guidelines

### Buttons

#### Solid vs Outline Buttons
- **Solid buttons** (`btn-primary`, `btn-danger`): Use for main form actions (Save, Submit, Create)
- **Outline buttons** (`btn-outline-*`): Use by default, especially for page-level actions and secondary actions

**Important**: Buttons in the top-right corner of pages (Edit, Delete, Back) should always be outline buttons to maintain visual hierarchy and avoid overwhelming the interface.

#### Primary Actions
```html
<!-- Form actions - solid -->
<button class="btn btn-primary">Save</button>
<button class="btn btn-primary">Submit</button>

<!-- Page actions - outline by default -->
<button class="btn btn-outline-primary">Create New</button>
<button class="btn btn-outline-primary">Edit</button>
<button class="btn btn-outline-primary">Add Package</button>
```

#### Destructive Actions
```html
<!-- Critical actions - can be solid if very important -->
<button class="btn btn-danger">Delete All</button>

<!-- Most delete actions - outline by default -->
<button class="btn btn-outline-danger">Delete</button>
<button class="btn btn-outline-danger">Remove</button>
```

#### Navigation/Secondary
```html
<a href="#" class="btn btn-outline-secondary">Back</a>
<a href="#" class="btn btn-outline-secondary">Cancel</a>
```

### Cards and Sections

#### Standard Card Header
```html
<div class="card-header bg-primary text-white">
    <h5 class="mb-0">Section Title</h5>
</div>
```

#### Warning Card
```html
<div class="alert alert-warning">
    <i class="fas fa-exclamation-triangle me-2"></i>
    Low stock warning message
</div>
```

#### Danger/Error Card
```html
<div class="alert alert-danger">
    <i class="fas fa-exclamation-circle me-2"></i>
    Critical error message
</div>
```

### Status Badges

#### Normal Status
```html
<span class="badge bg-primary">Active</span>
<span class="badge bg-primary">Sealed</span>
<span class="badge bg-primary">Processing</span>
```

#### Warning Status
```html
<span class="badge bg-warning text-dark">Expires Soon</span>
<span class="badge bg-warning text-dark">Low Stock</span>
```

#### Critical Status
```html
<span class="badge bg-danger">Expired</span>
<span class="badge bg-danger">Out of Stock</span>
```

### Tables

#### Standard Table
```html
<table class="table table-hover">
    <thead>
        <tr>
            <th>Column Header</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Data</td>
        </tr>
    </tbody>
</table>
```

#### Compact Table
```html
<table class="table table-sm table-hover">
    <!-- For dense information like logs -->
</table>
```

## View-Specific Guidelines

### Dashboard Views
- Use warning alerts for pre-alert states (low stock before next visit)
- Use danger alerts for critical states (completely out of stock)
- Primary color for all action buttons and metrics cards
- Consistent card header styling with `bg-primary`

### List Views (Products, Ingredients, etc.)
- Primary buttons for main actions ("Add New", "Import")
- Outline primary buttons for row actions ("Edit", "View")
- Danger buttons only for "Delete" when applicable
- Status badges follow the color system above

### Detail Views (Product Details, etc.)
- Primary color for card headers
- Primary badges for status indicators
- Information organized in clean white cards
- Action buttons follow button guidelines

### Form Views
- Primary submit buttons
- Outline secondary for cancel/back actions
- Validation errors in danger color
- Helper text in muted gray

### Settings Views
- Primary color for save actions
- Warning alerts for configuration notices
- Danger alerts for irreversible actions
- Clean card-based layout

### Scanner/Inventory Views
- Primary color for scan actions
- Warning badges for items expiring soon
- Danger badges for expired items
- Status progression uses primary color

### Reports/Analytics Views
- Primary color for chart elements and metrics
- Clean white backgrounds for readability
- Consistent typography hierarchy
- Action buttons follow standard guidelines

## Typography

### Headings
- Use Bootstrap heading classes (`h1`, `h2`, etc.)
- Maintain consistent hierarchy
- Keep headings concise and descriptive

### Body Text
- Default text color for primary content
- `text-muted` for secondary information
- `small` class for metadata and helper text

### Code/Technical Text
```html
<code>Technical identifiers</code>
<small class="text-muted">Metadata information</small>
```

## Spacing and Layout

### Standard Spacing
- Use Bootstrap spacing utilities consistently
- `mb-4` for section spacing
- `me-2` for icon spacing
- `p-3` or `p-4` for card padding

### Grid Layout
- Use Bootstrap grid system
- Maintain consistent breakpoints
- Responsive design principles

## Icons

### Icon Usage
- Font Awesome icons throughout
- Consistent icon choices for same actions
- Icons should support, not replace, text labels

### Common Icon Patterns
- `fas fa-plus` for add/create actions
- `fas fa-edit` for edit actions  
- `fas fa-trash` for delete actions
- `fas fa-eye` for view actions
- `fas fa-history` for logs/history
- `fas fa-exclamation-triangle` for warnings
- `fas fa-exclamation-circle` for errors

## Implementation Notes

### CSS Classes Priority
1. Use Bootstrap utility classes first
2. Custom CSS only when necessary
3. Maintain consistency with existing patterns
4. Document any custom components

### Accessibility
- Ensure color contrast meets WCAG guidelines
- Provide alternative text for icons
- Use semantic HTML elements
- Support keyboard navigation

### Browser Compatibility
- Design works in modern browsers
- Progressive enhancement approach
- Responsive design for all screen sizes

## Examples of Correct Usage

### ✅ Good Examples

#### Dashboard Warning
```html
<div class="alert alert-warning">
    <i class="fas fa-exclamation-triangle me-2"></i>
    Your Salbutamol will run out in 3 days, before your next visit on 2025-09-15.
</div>
```

#### Product Actions
```html
<a href="/products/new" class="btn btn-primary">Add Product</a>
<a href="/products/7/edit" class="btn btn-outline-primary">Edit</a>
<button class="btn btn-danger" onclick="confirmDelete()">Delete</button>
```

#### Status Badges
```html
<span class="badge bg-primary">Active</span>
<span class="badge bg-warning text-dark">Expires in 5 days</span>
<span class="badge bg-danger">Expired</span>
```

### ❌ Wrong Examples

#### Overuse of Colors
```html
<!-- DON'T DO THIS -->
<a href="/products/new" class="btn btn-success">Add Product</a>
<a href="/products/7/edit" class="btn btn-info">Edit</a>
<a href="/products/7/view" class="btn btn-warning">View</a>
```

#### Inconsistent Card Headers
```html
<!-- DON'T DO THIS -->
<div class="card-header bg-info">Section 1</div>
<div class="card-header bg-success">Section 2</div>
<div class="card-header bg-warning">Section 3</div>
```

## Testing Guidelines

### Visual Testing
- Check consistency across all views
- Verify color usage follows guidelines
- Test responsive behavior
- Validate accessibility requirements

### Code Review
- Ensure new components follow these guidelines
- Check for color disease patterns
- Verify semantic color usage
- Maintain documentation updates

---

**Remember: Consistency is key. When in doubt, use primary blue. Reserve colors for their specific semantic meaning only.**