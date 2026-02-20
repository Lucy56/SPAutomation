# Weekly Specials Newsletter Workflow

## Process Overview
When user requests weekly specials newsletter creation, follow this streamlined process with minimal questions.

## 1. Pattern Selection Strategy

### Primary Goal
Pull out **old stock that was selling good in the past** - patterns that have proven sales history but haven't been featured recently. This prevents valuable inventory from being overlooked.

### Selection Criteria (in priority order)
1. **Historical Performance**: Strong past sales (60-90 day window)
2. **Time Since Last Feature**: Check `weeklySpecials.json` - avoid patterns featured in last 4-6 weeks
3. **Seasonality**: Appropriate for current season/transition period
4. **Variety**: Mix of garment types (top, dress, sweater, etc.)
5. **Complementarity**: Patterns that work well together stylistically

### When User Suggests Patterns
- If user suggests 1-2 patterns: **Analyze and suggest complementary 3rd pattern**
  - Check co-purchase data for patterns bought together
  - Ensure variety in garment types
  - Verify seasonal appropriateness
- If user suggests 3 patterns: Proceed with their selection

### Analysis Queries
```sql
-- Find old stock with good historical sales (not featured recently)
SELECT
    p.product_id,
    p.title,
    SUM(li.quantity) as total_units,
    COUNT(DISTINCT o.order_id) as order_count,
    MAX(o.created_at) as last_sale
FROM line_items li
JOIN orders o ON li.order_id = o.order_id
JOIN products p ON li.product_id = p.product_id
WHERE o.created_at >= date('now', '-90 days')
    AND p.product_id NOT IN (recent_featured_patterns)
GROUP BY p.product_id
ORDER BY total_units DESC;
```

## 2. Newsletter Layout

### Fixed Structure
- **Top Row**: 2 patterns side-by-side (50% width each)
- **Bottom**: 1 pattern full-width (100%)
- Always responsive for mobile

## 3. Color Scheme Generation

### Process
1. **Analyze product images**: Extract dominant colors from the 3 selected pattern images
2. **Generate complementary palette**: Create cohesive color scheme that complements images
3. **Key Rule**: **DO NOT oversaturate with one color, especially in fonts** - this causes blending issues
4. **No "no green" rule**: Any color is acceptable if used appropriately

### Color Usage Guidelines
- Background: Lightest shade from palette
- Headers: Gradient using 2 complementary colors from images
- Buttons: Same gradient or solid accent color
- Body text: Neutral dark (don't oversaturate with accent color)
- Heading text: Slightly lighter than body but still readable
- Links: Accent color that stands out but harmonizes

## 4. Image Management

### S3 Structure
Images stored at: `s3://sinclairpatterns/MAIL/patterns/{PatternName}/`

### CloudFront URLs
Use: `https://d2ukt8mr71y5lh.cloudfront.net/MAIL/patterns/{PatternName}/{image_file}`

### Image Selection Priority
1. Check S3 for main product image (usually with pattern code like `t24.jpg`, `td29.jpg`)
2. If multiple options, prefer images showing full garment/model
3. Verify image exists before generating newsletter

### Image Upload (if needed)
- Fetch from Shopify product page
- Upload to S3: `s3://sinclairpatterns/MAIL/patterns/{PatternName}/`
- Set content-type appropriately

## 5. Product Data Collection

### Shopify API
```bash
curl https://sinclairpatterns.com/products/{handle}.json
```

### Required Fields
- Title
- Handle (for URL)
- Price
- Main image URL (for color analysis & upload)
- Variant IDs

## 6. Newsletter Generation

### Template Location
Reference: `/Users/sanna/Dev/Experiments/SinclairHelper/Docs/Newsletter.md`

### Key Elements
- Sale end date (typically Sunday, 7 days from creation)
- UTM tracking: `?utm_source=sendy&utm_medium=email&utm_campaign={date}-{theme}`
- Responsive design with mobile-first approach
- Email-safe inline CSS

### Output Files
1. HTML: `/Users/sanna/Dev/Experiments/SinclairHelper/Output/Newsletters/{date}-{theme}.html`
2. Metadata: `/Users/sanna/Dev/Experiments/SinclairHelper/Output/Newsletters/{date}-{theme}-metadata.json`

## 7. Sendy Integration

### Metadata Structure
```json
{
  "campaign": {
    "title": "Weekly Specials - {Theme} ({Date})",
    "subject": "{Compelling Subject Line}",
    "from_name": "Sinclair Patterns",
    "list_ids": "zDOpr87Nl7Wztkn2UnQRBg,olrPdvDTCPfq892TwO26oWUw,IHuKbEWHj5pcUcKTqA88Pg",
    "track_opens": 2,
    "track_clicks": 2,
    "send_campaign": 0
  }
}
```

### Upload Process
1. Create campaign as **DRAFT** (send_campaign: 0)
2. Use script: `/Users/sanna/Dev/Experiments/SinclairHelper/Scripts/sendy_connector.py`
3. Provide Sendy URL for user review: https://mail.sinclairpatterns.com

## 8. Tracking

### Update weeklySpecials.json
Add new entry:
```json
{
  "date": "2026-01-27",
  "patterns": ["Libby", "Sofia", "Dakota"],
  "theme": "RefinedWinterTransitions",
  "campaign_id": "{sendy_campaign_id}"
}
```

## 9. Streamlined Execution Checklist

When user says "create weekly specials" or similar:

- [ ] Query database for old stock with good historical sales
- [ ] Filter out patterns featured in last 4-6 weeks
- [ ] If user suggests patterns: analyze and suggest complementary option if needed
- [ ] Fetch product data from Shopify
- [ ] Verify images exist in S3 (upload if missing)
- [ ] Analyze product images for color palette
- [ ] Generate HTML newsletter with complementary colors
- [ ] Create metadata JSON
- [ ] Update weeklySpecials.json
- [ ] Upload to Sendy as DRAFT
- [ ] Provide Sendy URL for review

## 10. Subject Line Formulas

Generate 3-5 options following these patterns:
- Feature-focused: "{Pattern Names} on Special This Week"
- Benefit-focused: "Transition in Style: {Patterns} on Special"
- Urgency: "Last Chance: {Pattern Names} Sale Ends Sunday"
- Seasonal: "{Season} Essentials: {Patterns} Now on Sale"
- Value: "Save on {Patterns} - This Week Only"

## 11. Common Pitfalls to Avoid

❌ Don't focus only on recent momentum patterns
✅ Do prioritize good past sellers that need visibility

❌ Don't use fixed color schemes
✅ Do analyze images and create complementary palettes

❌ Don't oversaturate with one accent color (especially fonts)
✅ Do use varied colors with neutral text

❌ Don't create 3-column layouts
✅ Do use 2+1 layout (2 top, 1 bottom)

❌ Don't ask excessive questions
✅ Do make informed decisions based on data and this workflow
