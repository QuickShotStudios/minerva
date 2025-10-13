# Product Requirements Document
## Kindle Cloud Reader to Markdown Converter

### Project Overview
Automated tool to capture and convert Kindle Cloud Reader books into markdown documents using screenshots and AI-powered text extraction.

### Problem Statement
Users need to extract and convert content from Kindle Cloud Reader into markdown format for personal use, note-taking, or accessibility purposes. Manual copying is time-consuming and often restricted by DRM.

### Solution Approach
Python-based automation using Playwright for browser control, screenshot capture, and OpenAI GPT-4 Vision API for intelligent text extraction and markdown formatting.

---

## Core Requirements

### 1. Authentication & Session Management
- **Manual Login Flow**: Launch browser in visible mode for initial Amazon authentication
- **Session Persistence**: Save authentication state to reuse across multiple runs
- **Session Storage**: Store cookies and localStorage in secure local directory
- **Expiry Handling**: Detect expired sessions and prompt for re-authentication

### 2. Book Navigation & Screenshot Capture
- **Page Detection**: Identify current page and total page count
- **Navigation Methods**: 
  - Arrow key simulation (primary)
  - Click zone detection (fallback)
  - Swipe gesture emulation (if needed)
- **Screenshot Requirements**:
  - Full page capture at 1920x1080 resolution
  - Sequential naming convention (page_001.png, page_002.png)
  - PNG format for quality, with option to compress later
- **End Detection**: Identify last page through disabled buttons or page indicators
- **Progress Tracking**: Display current page/total pages during capture

### 3. Image Processing & Optimization
- **Batch Collection**: Group screenshots into batches of 5-10 for API efficiency
- **Image Optimization**:
  - Resize to max 1024px width while maintaining aspect ratio
  - Convert PNG to JPEG for token reduction (optional)
  - Compress without significant quality loss
- **Base64 Encoding**: Prepare images for API transmission

### 4. AI Text Extraction
- **OpenAI Integration**:
  - Use GPT-4V (gpt-4o-mini with vision) model
  - Low detail mode by default for cost optimization
  - High detail mode option for complex layouts
- **Prompt Engineering**:
  - Extract all text content preserving structure
  - Maintain headers, paragraphs, lists
  - Identify and preserve emphasis (bold, italic)
  - Remove UI elements and navigation artifacts
- **Batch Processing**: Send multiple pages per API call when possible

### 5. Markdown Generation
- **Content Structure**:
  - Preserve original book structure (chapters, sections)
  - Maintain text hierarchy (H1 for chapters, H2 for sections)
  - Format quotes, code blocks, lists appropriately
- **Page Markers**: Optional page number indicators in markdown
- **Metadata**: Include book title, author, capture date

### 6. Error Handling & Recovery
- **Checkpoint System**: Save progress after each page
- **Resume Capability**: Continue from last successful page after interruption
- **Rate Limiting**: Implement delays to avoid detection
- **API Failures**: Retry logic with exponential backoff
- **Partial Success**: Save what's captured even if process fails

---

## Technical Specifications

### Technology Stack

#### Core Language
- **Python 3.9+** - Primary development language
  - Chosen for superior async handling with Playwright
  - Better OpenAI client library support
  - Simpler error handling for sequential operations

#### Browser Automation
- **Playwright** - Web automation framework
  - Cross-browser support (Chromium preferred for Kindle)
  - Built-in wait strategies for dynamic content
  - Session state management capabilities
  - Stealth mode options for bot detection avoidance

#### AI/ML Services
- **OpenAI GPT-4 Vision API**
  - Model: `gpt-4o-mini` with vision capabilities
  - Low detail mode for cost optimization
  - Fallback: `gpt-4o` for complex layouts if needed
  - API client: `openai` Python package v1.0+

#### Image Processing
- **Pillow (PIL)** - Image manipulation
  - Screenshot optimization and compression
  - Format conversion (PNG to JPEG)
  - Resolution adjustment for API efficiency

#### Additional Libraries
- **python-dotenv** - Environment variable management
- **asyncio** - Asynchronous operation handling
- **pathlib** - Cross-platform file path handling
- **base64** - Image encoding for API transmission
- **json** - Configuration and session storage
- **logging** - Structured logging and debugging

### Environment Setup
- Python virtual environment (venv or conda)
- Environment variables: OPENAI_API_KEY
- Storage: Local directories for screenshots and session data

### File Structure
```
project/
├── kindle_session/      # Browser session data
├── screenshots/         # Captured pages
├── output/             # Generated markdown files
├── logs/               # Process logs
└── config.json         # User settings
```

### Configuration Options
- Start URL or book identifier
- Page range (optional: specific chapters/pages)
- Output format preferences
- Image quality settings
- API model selection
- Rate limiting parameters

---

## User Workflow

### Initial Setup
1. User runs script in setup mode
2. Browser launches visibly
3. User logs into Amazon Kindle Cloud Reader
4. User navigates to desired book
5. User confirms ready state
6. Script saves authentication session

### Automated Capture
1. Script loads saved session
2. Navigates to book/library
3. Begins screenshot capture loop
4. Displays progress in terminal
5. Processes images through AI
6. Generates final markdown file

### Output Delivery
- Single markdown file with complete book content
- Optional: Chapter-separated files
- Screenshots archive (optional retention)
- Process log for debugging

---

## Success Metrics
- **Accuracy**: 95%+ text extraction accuracy
- **Performance**: ~2-3 seconds per page total processing
- **Cost**: Under $0.50 per 100-page book
- **Reliability**: Successful completion rate >90%

## Constraints & Considerations
- Amazon ToS compliance (personal use only)
- DRM respect (no circumvention, only visual capture)
- API rate limits (OpenAI: 500 RPM for tier 1)
- Token limits (128k context window)
- Storage requirements (~5MB per page as PNG)

## Edge Cases & Advanced Handling

### 1. Two-Page Spread Detection

**Problem**: Kindle Cloud Reader sometimes displays two pages side-by-side on wider screens. Capturing this as one screenshot creates problems:
- Text order confusion (should read left page fully, then right page)
- Duplicate content if both pages are also captured individually
- Page count accuracy issues

**Solution**:
- Detect viewport width and identify if layout is showing 1 or 2 pages
- Use CSS selectors to identify page containers (`div[data-page-number]`)
- If dual-page mode detected:
  - Crop screenshot vertically at center point into two separate images
  - Process each half as separate pages
  - Or force single-page mode via viewport resize (1280x720)
- Prompt GPT-4V: "This image shows two book pages. Extract left page first, then right page. Mark with [PAGE BREAK]"

**Implementation**:
```python
# Detect page containers
page_elements = await page.locator('[class*="page"]').count()
if page_elements > 1:
    # Dual page mode - crop screenshot
    # OR resize viewport to force single page
    await page.set_viewport_size({"width": 1280, "height": 720})
```

### 2. Images/Diagrams Within Text

**Problem**: Current plan only extracts text, but books contain:
- Illustrations, charts, graphs
- Photos with captions
- Diagrams referenced in text ("see Figure 3.2")
- Cover art, chapter illustrations

**Solution**:
- **Detection**: Enhance GPT-4V prompt to identify non-text visual elements
  - "Identify any images, charts, or diagrams. Describe their position and content."
- **Extraction**: Save image region as separate file
  - Use Playwright to crop specific regions: `await page.locator('img').screenshot()`
  - Or use Pillow to crop from full screenshot based on GPT-4V coordinates
- **Storage**: `output/book_title/images/page_042_fig_01.png`
- **Markdown Integration**:
  - Insert reference: `![Diagram of water cycle](images/page_042_fig_01.png)`
  - Include caption if present
  - Add alt text with GPT-4V description for accessibility

**Enhanced Prompt**:
```
Extract all text. For any images/diagrams:
1. Describe: [what it shows]
2. Caption: [if present]
3. Position: [approximate % from top]
Output format: {{IMAGE: description | caption | position}}
```

**Post-processing**:
- Parse `{{IMAGE: ...}}` markers
- Extract that region from screenshot
- Replace marker with markdown image syntax

### 3. Footnotes and Endnotes Handling

**Problem**: Academic/non-fiction books use footnotes that appear:
- At bottom of page (footnotes)
- At end of chapter/book (endnotes)
- Inline as superscript numbers¹
- May span multiple pages

**Challenges**:
- Visual distinction from body text is subtle
- Maintaining reference integrity (superscript ¹ → footnote content)
- Endnotes separated from their references by many pages
- Same footnote number reused per chapter

**Solution**:

**Detection Phase**:
- GPT-4V prompt: "Identify footnotes (small text at bottom) separately from body text"
- Look for visual cues: smaller font, horizontal separator lines, superscript markers

**Markdown Format Options**:

*Option A - Inline references (preferred for markdown)*:
```markdown
This is a sentence with a reference[^1].

[^1]: This is the footnote content.
```

*Option B - Chapter endnotes*:
```markdown
## Chapter 3
Text with reference¹...

### Notes
1. Footnote content here
```

**Implementation Strategy**:
- Track footnote numbers per page/chapter
- Store footnote content in temporary buffer
- Insert at end of current section or page
- Validate references: ensure every superscript has matching note

**Enhanced prompt**:
```
Identify three text types:
1. BODY: Main content
2. FOOTNOTE_REF: Superscript numbers in text (mark as [^N])
3. FOOTNOTE_TEXT: Small text at bottom (format as [^N]: text)

Preserve footnote numbering exactly as shown.
```

### 4. Table of Contents Extraction

**Problem**: The PRD doesn't address how to:
- Identify book structure (parts, chapters, sections)
- Create navigable markdown TOC
- Link TOC entries to actual content
- Handle nested hierarchies

**Value**:
- Enables chapter-by-chapter processing
- Creates clickable navigation in markdown
- Helps validate completeness (did we get all chapters?)
- User can specify: "only capture chapters 3-7"

**Solution Approach**:

**Phase 1: Detect TOC in Reader**:
- Kindle Cloud Reader has built-in TOC menu
- Playwright: click TOC button, scrape the structure
```python
await page.click('[aria-label="Table of Contents"]')
toc_items = await page.locator('.toc-item').all_text_contents()
```

**Phase 2: Extract Structure Data**:
```python
toc_structure = {
    "Part 1: Introduction": {
        "page": 1,
        "chapters": {
            "Chapter 1: Getting Started": {"page": 3},
            "Chapter 2: Basics": {"page": 15}
        }
    }
}
```

**Phase 3: Markdown Generation**:
```markdown
# Book Title

## Table of Contents
- [Part 1: Introduction](#part-1-introduction)
  - [Chapter 1: Getting Started](#chapter-1-getting-started)
  - [Chapter 2: Basics](#chapter-2-basics)

---

## Part 1: Introduction
### Chapter 1: Getting Started
[content...]
```

**Phase 4: Validation**:
- As pages are processed, detect chapter headings via GPT-4V
- Cross-reference detected headings with TOC structure
- Flag mismatches: "Expected 'Chapter 3' on page 45, found 'Chapter 4'"
- Insert anchor markers at chapter boundaries

**Benefits**:
- Auto-generate proper heading hierarchy (H1/H2/H3)
- Enable partial captures: "capture just Chapter 5"
- Quality check: missing chapters detected early
- Better markdown structure without manual editing

**Implementation**:
```python
# 1. Extract TOC first
toc = await extract_table_of_contents(page)

# 2. During capture, validate against TOC
current_chapter = toc.get_chapter_by_page(page_num)
extracted_text = await process_with_gpt4v(screenshot)

# 3. Verify heading matches expectation
if current_chapter and not chapter_heading_matches(extracted_text, current_chapter):
    log.warning(f"Page {page_num}: Expected {current_chapter}, check quality")

# 4. Insert proper markdown headings
markdown += f"\n\n## {current_chapter['title']}\n\n{extracted_text}"
```

---

## Future Enhancements
- Multiple book batch processing
- Direct ePub generation
- Highlight and note extraction
- Local LLM option for privacy

---

## Implementation Phases

### Phase 1: Core Functionality
- Basic authentication and session management
- Simple page navigation
- Screenshot capture
- Basic AI text extraction

### Phase 2: Optimization
- Image compression
- Batch processing
- Error recovery
- Progress persistence

### Phase 3: Enhancement
- Advanced markdown formatting
- Metadata extraction
- Configuration UI
- Multiple output formats