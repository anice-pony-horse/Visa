# Streamlit Visa Exhibit Generator

**Standalone application for generating professional numbered exhibit packages from PDFs, folders, and Google Drive.**

## Features

- 📁 **Multiple Input Sources**
  - Direct PDF uploads
  - ZIP file/folder batch uploads
  - Google Drive folder integration
  - URL to PDF conversion (with API2PDF)

- 📄 **Professional Output**
  - Automatic exhibit numbering (A, B, C... or 1, 2, 3... or I, II, III...)
  - Professional Table of Contents
  - Merged single PDF package
  - Individual exhibit downloads

- 🌐 **URL Archiving**
  - Automatic archive.org preservation
  - Both original and archived URLs in TOC
  - Ensures long-term accessibility

- ⚡ **User Experience**
  - Drag-and-drop interface
  - Real-time progress tracking
  - Preview before generation
  - Multiple numbering styles

## Quick Start

### 1. Install Dependencies

```bash
cd /home/innovativeautomations/Visa\ Exhibit\ Maker/streamlit-exhibit-generator
pip install -r requirements.txt
```

### 2. Run the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Usage Guide

### Upload Files (Tab 1)

1. **Individual Files**: Drag and drop PDFs or click to browse
2. **Folder/Batch**: Upload a ZIP file containing all exhibits
3. Click "Add Files to Exhibit List"

### Add URLs (Tab 2)

1. Paste URLs (one per line)
2. URLs will be:
   - Archived to archive.org
   - Converted to PDF (requires API2PDF key)
   - Added to exhibit list

### Google Drive (Tab 3)

**Prerequisites**:
- Google Cloud Project with Drive API enabled
- Service account credentials JSON file

**Steps**:
1. Upload credentials in sidebar
2. Paste Google Drive folder URL
3. Click "Import Folder"
4. All PDFs in folder will be added to exhibit list

### Generate (Tab 4)

1. Review exhibit list
2. Reorder exhibits (drag/drop or delete)
3. Enter case name and beneficiary name
4. Click "Generate Exhibit Package"
5. Download:
   - Complete merged PDF
   - Table of Contents
   - Individual exhibits

## Google Drive Setup

### Creating Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Enable Google Drive API
4. Create Service Account:
   - IAM & Admin → Service Accounts → Create
   - Grant "Viewer" role
   - Create key (JSON format)
5. Share your Drive folder with service account email
6. Upload credentials JSON in app sidebar

### Sharing Folder

```
Right-click folder → Share → Add service account email
Example: exhibit-generator@my-project.iam.gserviceaccount.com
Role: Viewer
```

## Configuration

### API2PDF (Optional)

For URL to PDF conversion:

1. Get API key from [api2pdf.com](https://www.api2pdf.com/)
2. Enter in sidebar under "API Configuration"

### Environment Variables

Create `.env` file (optional):

```bash
API2PDF_API_KEY=your_api2pdf_key_here
```

## File Structure

```
streamlit-exhibit-generator/
├── app.py                    # Main Streamlit application
├── exhibit_processor.py      # Core exhibit processing logic
├── pdf_handler.py           # PDF operations (merge, number, TOC)
├── google_drive.py          # Google Drive integration
├── archive_handler.py       # Archive.org integration
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Features by Tab

| Tab | Feature | Status |
|-----|---------|--------|
| Upload Files | Direct file upload | ✅ Working |
| Upload Files | ZIP extraction | ✅ Working |
| Add URLs | URL input | ✅ Working |
| Add URLs | archive.org archiving | ✅ Working |
| Add URLs | URL to PDF | ⚠️ Requires API2PDF |
| Google Drive | Folder import | ✅ Working |
| Google Drive | Recursive folders | ✅ Working |
| Generate | Table of Contents | ✅ Working |
| Generate | PDF merging | ✅ Working |
| Generate | Exhibit numbering | ✅ Working |

## Examples

### Example 1: Simple PDF Upload

1. Upload 5 PDFs
2. Click "Add Files to Exhibit List"
3. Go to Generate tab
4. Enter case name: "Smith_O1_Visa"
5. Click "Generate Exhibit Package"
6. Download merged PDF

### Example 2: Google Drive Folder

1. Upload service account JSON in sidebar
2. Go to Google Drive tab
3. Paste folder URL: `https://drive.google.com/drive/folders/ABC123...`
4. Click "Import Folder"
5. Review exhibits in Generate tab
6. Generate package

### Example 3: Mixed Sources

1. Upload 3 PDFs (Tab 1)
2. Add 5 URLs (Tab 2)
3. Import Drive folder with 10 files (Tab 3)
4. Total: 18 exhibits (A through R)
5. Generate merged package

## Troubleshooting

### Google Drive Not Working

**Error**: "Not authenticated"
- Solution: Upload valid service account JSON

**Error**: "Folder not found"
- Solution: Share folder with service account email

**Error**: "Permission denied"
- Solution: Grant "Viewer" access to service account

### PDF Generation Issues

**Error**: "Failed to merge PDFs"
- Solution: Ensure all files are valid PDFs
- Check file isn't password-protected

**Large files taking long**
- Expected: Processing 100+ exhibits takes time
- Monitor progress bar

### Archive.org Issues

**Error**: "Archive failed"
- Archive.org may be temporarily unavailable
- App will continue with original URL

**Slow archiving**
- Normal: 1 second delay between URLs
- Prevents rate limiting

## Deployment

### Streamlit Cloud (Free)

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repository
4. Deploy!

### Local Network

```bash
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

Access from other devices: `http://YOUR_IP:8501`

## Roadmap

- [ ] OCR for scanned documents
- [ ] Bookmarks in merged PDF
- [ ] Custom exhibit templates
- [ ] Batch case processing
- [ ] Database storage
- [ ] Email delivery
- [ ] Collaboration features

## Support

For issues or questions:
- Check troubleshooting section
- Review example PDFs in `../Examples of Single PDFs/`
- Contact developer

## License

Internal use only - Innovative Automations

---

**Built**: November 2025
**Version**: 1.0
**Status**: Production Ready
