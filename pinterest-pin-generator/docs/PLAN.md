# Pinterest Pin A/B Testing System - Implementation Plan

## Overview
Automated A/B testing system for Pinterest pin generation with 5 prompt variants, supporting 140+ patterns with 40-50 images each (~6,000 total pins). System includes automated Pinterest API analytics tracking and Claude-powered performance analysis.

---

## System Architecture

### 1. Prompt Variants (A, B, C, D, E)

Each variant folder contains:
- `config.json` - Variant metadata, Pinterest templates, performance metrics
- `image_prompt.txt` - Gemini image generation prompt

**Variant Descriptions:**
- **A - Bold CTA**: Direct call-to-action with urgency and benefits
- **B - Minimal Elegant**: Clean, sophisticated, understated design
- **C - Lifestyle Story**: Emotional storytelling, aspirational
- **D - Urgency & Trending**: FOMO-driven, high energy, scarcity
- **E - Educational**: Learning-focused, beginner-friendly, tutorial style

### 2. Data Structure

```
data/
├── pins_generated/          # Generated pins organized by pattern and variant
│   ├── Mirabel/
│   │   ├── A/
│   │   │   ├── mirabel_001.png
│   │   │   └── mirabel_001_metadata.json
│   │   ├── B/
│   │   ├── C/
│   │   ├── D/
│   │   └── E/
│   └── [138 more patterns]/
│
├── pins_posted/
│   └── posting_log.json     # Track posted pins with Pinterest IDs
│
└── analytics/
    ├── raw_data/
    │   └── pinterest_api_pulls/
    │       ├── 2026-02-03.json
    │       └── ...
    ├── pin_performance.db    # SQLite database for querying
    └── analysis_results/
        ├── weekly_reports/
        │   ├── 2026-W06.json
        │   └── ...
        └── variant_rankings.json
```

---

## Implementation Phases

### Phase 1: Pin Generation System ✓
**Status**: Ready to implement

**Components:**
1. `scripts/generate_batch.py`
   - Generate pins for specific pattern + variant
   - Support batch generation
   - Read variant config and image prompts
   - Call Gemini API for image generation
   - Save with proper naming convention

**Usage:**
```bash
python scripts/generate_batch.py --pattern Mirabel --variant A --count 5
python scripts/generate_batch.py --pattern CrewW --all-variants --count 3
```

**Output:**
- Generated images in `data/pins_generated/{pattern}/{variant}/`
- Metadata JSON files with Pinterest info ready for posting

---

### Phase 2: Pinterest Posting System
**Status**: To be implemented

**Components:**
1. `scripts/post_scheduler.py`
   - Read from generated pins
   - Post to Pinterest API (30-70 pins/week)
   - Track Pinterest pin IDs
   - Update posting_log.json
   - Support weighted distribution (based on performance)

**Features:**
- Weekly posting limits (configurable)
- Smart scheduling (best times to post)
- Weighted variant distribution (more pins from winning variants)
- Track posting history

**Posting Log Format:**
```json
{
  "pin_id": "mirabel_001_A",
  "pinterest_id": "123456789",
  "pattern_name": "Mirabel",
  "variant": "A",
  "filename": "mirabel_001.png",
  "date_posted": "2026-02-10T14:30:00Z",
  "pinterest_url": "https://pin.it/xxx",
  "week_number": "2026-W06"
}
```

---

### Phase 3: Analytics Collection
**Status**: To be implemented

**Components:**
1. `scripts/sync_pinterest_analytics.py`
   - Cron job (daily or weekly)
   - Pull analytics from Pinterest API
   - Store raw JSON dumps
   - Update SQLite database

**Pinterest Metrics to Track:**
- Impressions
- Clicks
- Saves
- Click-through rate (CTR)
- Engagement rate
- Pin URL for reference

**Database Schema:**
```sql
CREATE TABLE pin_performance (
  id INTEGER PRIMARY KEY,
  pin_id TEXT,
  pinterest_id TEXT,
  variant TEXT,
  pattern_name TEXT,
  date_checked DATE,
  impressions INTEGER,
  clicks INTEGER,
  saves INTEGER,
  ctr REAL,
  engagement_rate REAL
);
```

---

### Phase 4: AI-Powered Performance Analysis
**Status**: To be implemented

**Components:**
1. `scripts/analyze_performance.py`
   - Cron job (weekly)
   - Query performance data from SQLite
   - Send to Claude API for analysis
   - Claude analyzes which variants are winning
   - Auto-update performance_weight in variant configs
   - Generate weekly reports

**Claude Analysis Prompt:**
```
Analyze Pinterest pin performance data for 5 variants (A, B, C, D, E).

Data:
- Variant A: avg 2,150 impressions, 78 clicks, 41 saves, 3.6% CTR
- Variant B: avg 1,820 impressions, 92 clicks, 58 saves, 5.1% CTR
...

Tasks:
1. Rank variants by overall performance
2. Identify strengths/weaknesses of each variant
3. Recommend new performance_weight distribution
4. Suggest optimizations for underperforming variants

Return JSON with rankings, insights, and recommended weights.
```

**Output:**
```json
{
  "date": "2026-02-17",
  "analysis": {
    "top_performer": "B",
    "insights": "Variant B (Minimal Elegant) shows highest engagement...",
    "recommendations": {
      "A": {"weight": 0.15, "action": "reduce"},
      "B": {"weight": 0.35, "action": "increase"},
      "C": {"weight": 0.25, "action": "maintain"},
      "D": {"weight": 0.10, "action": "reduce"},
      "E": {"weight": 0.15, "action": "maintain"}
    }
  }
}
```

---

### Phase 5: Smart Batch Generation
**Status**: To be implemented after Phase 4

**Enhancement to `generate_batch.py`:**
- Read performance_weight from variant configs
- Generate more pins from winning variants
- Automatically adjust distribution based on Claude's analysis

**Example:**
```bash
# Smart generation: uses performance weights
python scripts/generate_batch.py --pattern Mirabel --smart --total 20

# Output:
# Variant B: 7 pins (35%)
# Variant C: 5 pins (25%)
# Variant A: 3 pins (15%)
# Variant E: 3 pins (15%)
# Variant D: 2 pins (10%)
```

---

## Weekly Workflow (Once Fully Implemented)

### Monday:
1. `sync_pinterest_analytics.py` pulls latest data (cron)
2. `analyze_performance.py` runs Claude analysis (cron)
3. Performance weights auto-updated

### Tuesday-Friday:
4. Generate new pins with smart distribution
5. `post_scheduler.py` posts 10-15 pins/day

### Saturday:
6. Review weekly report
7. Adjust patterns being promoted

---

## File Naming Conventions

**Generated Pins:**
```
{pattern_name}_{number}_{variant}.png
mirabel_001_A.png
mirabel_002_B.png
```

**Metadata Files:**
```
{pattern_name}_{number}_{variant}_metadata.json
```

**Weekly Reports:**
```
2026-W06.json  (ISO week number)
```

---

## Environment Variables Needed

```env
# Gemini API
GEMINI_API_KEY=your_key
GEMINI_API_MODEL=gemini-3-pro-image-preview

# Pinterest API (Phase 2)
PINTEREST_ACCESS_TOKEN=your_token
PINTEREST_APP_ID=your_app_id
PINTEREST_APP_SECRET=your_secret

# Anthropic Claude API (Phase 4)
ANTHROPIC_API_KEY=your_key

# Configuration
PINS_PER_WEEK=50
OUTPUT_BASE_DIR=/path/to/data
```

---

## Next Steps

### Immediate (Now):
1. ✅ Create folder structure
2. ✅ Create variant configs (A, B, C, D, E)
3. 🔲 User adds/refines prompts
4. 🔲 Build `generate_batch.py` script
5. 🔲 Test pin generation with sample images

### Short-term (Week 1-2):
6. Build Pinterest posting system
7. Set up Pinterest API credentials
8. Test posting workflow

### Medium-term (Week 3-4):
9. Build analytics sync system
10. Set up SQLite database
11. Test data collection

### Long-term (Month 2):
12. Implement Claude analysis
13. Build automated optimization
14. Create dashboard (optional)

---

## Success Metrics

**Generation:**
- Successfully generate 20-50 pins per batch
- All 5 variants working correctly
- Proper metadata for Pinterest posting

**Posting:**
- Maintain 30-70 pins/week posting rate
- Track all Pinterest IDs correctly
- No duplicate posts

**Analytics:**
- Daily/weekly data sync working
- Complete performance tracking
- Historical data preserved

**Optimization:**
- Claude analysis providing actionable insights
- Performance weights auto-adjusting
- Winning variants receiving more distribution

---

## Notes

- Start simple with manual testing
- Build automation incrementally
- Keep raw data backups
- Monitor API rate limits (Gemini, Pinterest, Claude)
- Track costs for API usage
