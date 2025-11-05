# Invoice Designer - Add & Delete Fields Guide

## Overview
The invoice designer now supports adding custom fields, deleting fields, and duplicating fields to create flexible invoice layouts.

## Adding New Fields

### Method 1: Using the Sidebar (Recommended)
Located in the right panel under "Add New Field":

1. **Text Field** - Editable text area for custom content
2. **Label & Input** - Form label with input field
3. **Image/Logo** - Placeholder for images
4. **Table** - Multi-column data table
5. **Divider Line** - Horizontal separator line

**Steps:**
1. Click the button for the field type you want
2. Field appears on the invoice
3. Field is automatically selected
4. Drag to position, resize as needed
5. Edit content by clicking inside

### Method 2: Using the Toolbar
Click the **"Add Field"** dropdown in the toolbar for quick access to all field types.

### Method 3: Keyboard Shortcuts (Coming Soon)
- `Ctrl + T` - Add Text Field
- `Ctrl + L` - Add Label Field

## Deleting Fields

### Protected Fields (Cannot Delete)
These core invoice fields are protected and cannot be deleted:
- Company Logo
- Company Name
- Company Address
- Invoice Title
- Invoice Details
- Customer Section
- Items Table
- Totals Section

### Deleting Custom Fields

**Method 1: Delete Button**
1. Select the field you want to delete
2. Click **"Delete Field"** button (red button in sidebar)
3. Confirm deletion in the popup dialog

**Method 2: Keyboard Shortcut**
1. Select the field
2. Press `Delete` key
3. Confirm deletion

**Features:**
- ✅ Confirmation dialog prevents accidental deletion
- ✅ Success message after deletion
- ✅ Only custom fields can be deleted
- ✅ Protected fields show error message

## Duplicating Fields

Create copies of existing fields with all styling and content preserved.

**Method 1: Duplicate Button**
1. Select the field you want to duplicate
2. Click **"Duplicate Selected"** button (green button in sidebar)
3. Copy appears offset from original

**Method 2: Keyboard Shortcut**
1. Select the field
2. Press `Ctrl + D`
3. Copy is created and selected

**Method 3: Toolbar Menu**
1. Click **"Add Field"** dropdown
2. Select **"Duplicate Selected"**

**Features:**
- ✅ Preserves all content and styling
- ✅ Automatically offsets position (20px right, 20px down)
- ✅ Unique ID assigned to copy
- ✅ Copy is automatically selected
- ✅ Works with any field type

## Field Types Explained

### 1. Text Field
**Use for:** Custom text, notes, terms & conditions, disclaimers

**Features:**
- Directly editable (click to type)
- Supports rich text formatting
- Resizable

**Example Uses:**
- Payment terms
- Thank you message
- Custom notes
- Terms and conditions

### 2. Label & Input
**Use for:** Form-style data entry fields

**Features:**
- Label above input field
- Styled form controls
- Good for additional invoice fields

**Example Uses:**
- Purchase Order Number
- Reference Number
- Delivery Date
- Special Instructions

### 3. Image/Logo
**Use for:** Additional logos, stamps, signatures

**Features:**
- Placeholder with icon
- Resizable
- Can be replaced with actual images

**Example Uses:**
- Secondary logo
- Certification badge
- Signature placeholder
- QR code placeholder

### 4. Table
**Use for:** Additional itemized data

**Features:**
- Bootstrap styled table
- Editable cells
- Resizable
- 3 columns by default

**Example Uses:**
- Additional charges breakdown
- Payment schedule
- Delivery schedule
- Custom itemization

### 5. Divider Line
**Use for:** Visual separation

**Features:**
- Horizontal line
- Customizable thickness
- Width adjustable

**Example Uses:**
- Section separators
- Visual breaks
- Grouping related content

## Tips & Best Practices

### Layout Organization
1. **Start with structure** - Add dividers and containers first
2. **Group related fields** - Use proximity and dividers
3. **Layer management** - Use z-index controls for overlapping fields
4. **Consistent spacing** - Use grid snap for alignment

### Efficient Workflow
1. **Use duplicate for similar fields** - Create one, duplicate, then modify
2. **Name your fields** - Field IDs help identify elements
3. **Test before saving** - Preview to check layout
4. **Save frequently** - Use Save button often

### Field Placement
1. **Keep within printable area** - Green border shows safe zone
2. **Avoid overlapping important content** - Use layer controls
3. **Consider print margins** - 15mm margin on all sides
4. **Test on actual printer** - Preview before finalizing

## Keyboard Shortcuts Summary

| Action | Shortcut | Description |
|--------|----------|-------------|
| Delete Field | `Delete` | Delete selected field |
| Duplicate Field | `Ctrl + D` | Duplicate selected field |
| Move Field | `Arrow Keys` | Move 2px (hold Shift for 10px) |
| Resize Field | `Ctrl + Arrow Keys` | Resize by 2px |
| Bring to Front | `Ctrl + ]` | Move to top layer |
| Send to Back | `Ctrl + [` | Move to bottom layer |
| Clear Selection | `Esc` | Deselect current field |

## Common Workflows

### Adding a Payment Terms Section
1. Click **"Add Field" → "Divider Line"**
2. Position above totals section
3. Click **"Add Field" → "Text Field"**
4. Type payment terms
5. Resize and position as needed

### Creating a Signature Block
1. Click **"Add Field" → "Image/Logo"**
2. Resize to signature size (200x100)
3. Add **"Divider Line"** below
4. Add **"Text Field"** for signature label
5. Duplicate for multiple signatures

### Custom Invoice Footer
1. Add **"Divider Line"** at bottom
2. Add **"Text Field"** for company details
3. Add another **"Text Field"** for legal text
4. Align and size appropriately

## Troubleshooting

### "Field cannot be deleted" Error
**Cause:** Trying to delete a protected core field
**Solution:** Only custom fields (those you added) can be deleted

### Duplicate button is disabled
**Cause:** No field is selected
**Solution:** Click on a field first to select it

### Field appears off-screen
**Cause:** Field placed outside printable area
**Solution:** Drag field back into green border area

### Can't select overlapping fields
**Cause:** Field is behind another field
**Solution:** Use layer controls to bring to front

### Changes not saving
**Cause:** Haven't clicked Save button
**Solution:** Click "Save" in toolbar after making changes

## Advanced Features

### Field Properties
When a field is selected, you can modify:
- **Position** (X, Y coordinates)
- **Size** (Width, Height)
- **Font** (Family, Size, Color)
- **Alignment** (Left, Center, Right)
- **Layer** (Z-index for stacking)

### Grid & Snap
- **Grid** - Visual guide for alignment
- **Snap** - Auto-align to grid (10px increments)
- Hold `Alt` while dragging to disable snap temporarily

### Export/Import Layout
- **Export** - Save your custom layout as JSON
- **Import** - Load a previously saved layout
- Useful for template reuse

---

**Last Updated:** October 26, 2025
**Version:** 2.0
