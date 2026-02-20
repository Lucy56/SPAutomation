# Pinterest Pin A/B Testing System

Automated system for generating and testing Pinterest pins with multiple prompt variants, powered by Gemini image generation, Pinterest API analytics, and Claude AI performance analysis.

## Quick Start

### 1. Current Setup (Ready to Use)

The folder structure and variant prompts are ready:

```
prompt_variants/
├── A/  (Bold CTA)
├── B/  (Minimal Elegant)
├── C/  (Lifestyle Story)
├── D/  (Urgency & Trending)
└── E/  (Educational)
```

### 2. Add Your Prompts

Edit the prompt files in each variant folder:
- `prompt_variants/A/image_prompt.txt`
- `prompt_variants/B/image_prompt.txt`
- etc.

### 3. Test Pin Generation

Once `generate_batch.py` is built, you can test:

```bash
python scripts/generate_batch.py --pattern Mirabel --variant A --count 1
```

---

## Folder Structure

```
pinterest-pin-generator/
├── prompt_variants/        # 5 variants (A, B, C, D, E)
│   └── A/
│       ├── config.json     # Variant settings & Pinterest metadata
│       └── image_prompt.txt # Gemini image generation prompt
│
├── data/
│   ├── pins_generated/     # Output organized by pattern/variant
│   ├── pins_posted/        # Posting logs
│   └── analytics/          # Performance tracking
│
├── scripts/                # Automation scripts
├── docs/                   # Documentation
│   └── PLAN.md            # Full implementation plan
└── README_AB_TESTING.md   # This file
```

---

## Variant Overview

| Variant | Name | Style | Best For |
|---------|------|-------|----------|
| **A** | Bold CTA | High-energy, direct, action-oriented | Quick conversions, impulse buyers |
| **B** | Minimal Elegant | Clean, sophisticated, understated | Premium audience, design-focused |
| **C** | Lifestyle Story | Warm, aspirational, emotional | Community building, engagement |
| **D** | Urgency & Trending | FOMO-driven, high contrast, urgent | Viral potential, trending patterns |
| **E** | Educational | Trustworthy, learning-focused | Beginners, skill-builders |

---

## Configuration Files

### config.json
Contains variant metadata and Pinterest posting templates:

```json
{
  "variant_name": "Bold CTA",
  "variant_id": "A",
  "pinterest_metadata_template": {
    "title": "{pattern_name} - Easy PDF Sewing Pattern",
    "description": "...",
    "keywords": [...],
    "hashtags": [...]
  },
  "performance_weight": 0.20
}
```

### image_prompt.txt
Gemini prompt for image generation. Variables available:
- `{pattern_name}` - Pattern name (e.g., "Mirabel")
- `{garment_type}` - Type of garment (e.g., "dress", "top")

---

## Workflow

### Phase 1: Generation (Current)
1. User adds/refines prompts in variant folders
2. Run `generate_batch.py` to create pins
3. Review generated pins manually

### Phase 2: Posting (Future)
4. Use `post_scheduler.py` to post 30-70 pins/week
5. Track posting in `posting_log.json`

### Phase 3: Analytics (Future)
6. `sync_pinterest_analytics.py` pulls Pinterest data (cron)
7. Data stored in SQLite database

### Phase 4: AI Optimization (Future)
8. `analyze_performance.py` sends data to Claude
9. Claude ranks variants and updates performance weights
10. System automatically generates more pins from winning variants

---

## Next Steps

1. **Now**: Refine prompts in `prompt_variants/*/image_prompt.txt`
2. **Next**: Build and test `generate_batch.py`
3. **Then**: Generate test batch with all 5 variants
4. **Later**: Implement Pinterest posting and analytics

See `docs/PLAN.md` for full implementation details.

---

## Tips for Prompt Writing

**Good prompts:**
- Clear, specific requirements
- Consistent structure across variants
- Use placeholder variables `{pattern_name}`, `{garment_type}`
- Define visual style clearly
- Specify Pinterest best practices

**Avoid:**
- Vague instructions
- Contradictory requirements
- Overly complex prompts
- Hard-coding pattern names

---

## Scaling

**Current capacity:**
- 140 patterns
- 40-50 images per pattern
- 5 variants
- **Total: ~28,000-35,000 possible pins**

**Posting strategy:**
- 30-70 pins/week
- Weighted distribution based on performance
- Continuous optimization via AI analysis

---

## Questions?

Refer to:
- `docs/PLAN.md` - Full implementation plan
- `prompt_variants/*/config.json` - Variant configurations
- Individual variant folders - Prompt examples
