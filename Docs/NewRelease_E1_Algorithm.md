# New Release E1 Email - Creation Algorithm

## Overview

E1 is the first email in the 3-part new release sequence. It introduces the pattern, showcases tester photos, includes testimonials, and features 2 weekly specials at the bottom.

---

## Step 1 - Gather Pattern Data

Fetch from `https://sinclairpatterns.com/products/[product-handle].json`

Extract:
- Product title (for pattern name and type)
- Body HTML (for description and options)
- Price (launch/special price)
- Compare-at price (regular price)
- Product handle (for URL construction)

**Product URL format:**
```
https://sinclairpatterns.com/products/[handle]
```

---

## Step 2 - Gather Weekly Specials Data

For each of the 2 weekly special patterns, fetch from their `.json` URL.

Extract:
- Pattern name (short display name, e.g. "Pebble knit top")
- Price (sale price)
- Compare-at price (regular price)
- Product handle (for URL)
- First image (download from Shopify CDN, upload to S3)

**URL format for specials:** Strip any `/collections/[collection-name]/` prefix:
```
https://sinclairpatterns.com/products/[handle]
```

---

## Step 3 - Prepare Images

### New Release Images (provided in `Output/New releases/[PatternName]/`)

| Local filename | S3 destination | Usage |
|---|---|---|
| `[name]_facebook_square.jpg` | `Helen/helen_facebook_square.jpg` | Hero image (full width) |
| `1.jpg` | `Helen/tester1.jpg` | Tester photo 1 |
| `2.jpg` | `Helen/tester2.jpg` | Tester photo 2 |
| `3.jpg` | `Helen/tester3.jpg` | Tester photo 3 |
| `4.jpg` | `Helen/tester4.jpg` | Tester photo 4 |
| `5.jpg` | `Helen/tester5.jpg` | Tester photo 5 |
| `6.jpg` | `Helen/tester6.jpg` | Tester photo 6 (if available) |
| `tech_*.png` | `Helen/tech_drawing.png` | Technical drawing |

### Weekly Specials Images
- Download first product image from Shopify CDN
- Upload to `s3://sinclairpatterns/MAIL/patterns/[PatternName]/special.jpg`

### S3 Upload Command
```bash
aws s3 cp [local_file] s3://sinclairpatterns/MAIL/patterns/[PatternName]/[filename] --content-type "image/jpeg"
```

### CloudFront Base URL
```
https://d2ukt8mr71y5lh.cloudfront.net/MAIL/patterns/[PatternName]/[filename]
```

---

## Step 4 - Write Email Content

### Campaign ID
Format: `[patternname]_e1` (lowercase, no spaces), e.g. `helen_e1`

### Preheader text
One sentence teaser, e.g.:
> "New: Helen pull on pants - fitted knit pants with yoke & contoured waistband. Special launch price $7.99!"

### Pattern name in header
Format: `New pattern release: [Name] [type]`
- Name = short name (e.g. Helen)
- Type = garment type in plain words (e.g. "pull on pants", "knit top", "hoodie")
- No em dashes, no fancy punctuation

### Intro paragraph
Formula:
> "Meet our new pattern [Name] - [garment description] with [key feature 1] and [key feature 2]. [Name] works perfectly for [use cases]."

- No "flatter/flattering" - describe the design feature instead
- No "drafted for [fabric]" - say "designed for [fabric]" or omit
- No French terry - use ponte, double knit, scuba, medium weight crepe

### Second paragraph
Describe the key design details and unique selling points:
- Fit and comfort details
- Inseam options (include actual measurements: e.g. "29/31/33" for heels, 27/29/31" for flats - Petite/Regular/Tall")
- Pocket options
- End with a short punchy line, e.g. "A quick sew you will reach for again and again."

### Options list (smaller font, 13px)
Bullet list including:
- Leg/style options
- Inseam lengths with measurements
- Pocket options (side and back separately if different)
- Waistband details
- Heights: Petite / Regular / Tall
- Size range: US0-US30 (no em dashes, use hyphen)
- Formats: A4, Letter, A0 and Projector
- Difficulty level
- Tutorial page count

### Special price line
Format (two lines, not an h3):
```
[Name] is on special until [Month Day, Year]
~~$[regular]~~  $[sale] (red)
```

### Tester photos
- Include all available tester photos (4-6)
- Width: 80%, max-width: 480px, centered
- Each links to product URL with UTM params

### Tester quotes
- Fix grammar but keep the tester's voice
- No em dashes - use hyphens or restructure
- Format: italic quote on one line, "- Name" in smaller muted gray below
- 4 quotes preferred
- If not yet available, leave HTML comments as placeholders

### Tech drawing
- Full width with 20px side padding
- max-width: 560px
- Links to product URL

---

## Step 5 - Weekly Specials Section

Heading: **"Pair up with our weekly specials"** (above the 2-column grid)

Two-column layout (50% each, stacks on mobile):

Each column contains:
1. Dark gradient header with pattern short name
2. Image (max-width 270px)
3. Short display name (bold, 15-16px)
4. Price: ~~$regular~~ **$sale** (red, 19px)
5. 1-2 sentence description (no em dashes)
6. "Shop Now" orange button

**Pattern display names:** Use short names only
- "Pebble knit top" not "Pebble henley style top and dress"
- "Estelle knit tee" not "Estelle over shoulder flounce knit tee"

---

## Step 6 - Nav Links

Three links on white background, separated from dark header below by a light border:

| Label | URL |
|---|---|
| + Shop women's patterns | `sinclairpatterns.com/collections/all-sewing-patterns` |
| + Shop men's patterns | `sinclairpatterns.com/collections/mens-patterns/` |
| + Shop kids' patterns | `sinclairpatterns.com/collections/kids-sewing-patterns` |

All links include UTM params: `?ref=tm&utm_source=S&utm_medium=email&utm_campaign=[campaign_id]`

---

## Step 7 - Footer

```
[View as a Web Page]
This email was sent to [Email].
You received this email because you are registered with Sinclair Patterns.
All prices stated in the email are in US Dollars.

Sinclair Patterns
Gold Coast, QLD Australia

[Unsubscribe]   ← use href="[unsubscribe]" Sendy tag
```

---

## Step 8 - Upload to Sendy

```bash
curl -s https://mail.sinclairpatterns.com/api/campaigns/create.php \
  -d "api_key=9beSlQPv8LFt5tZP9cP2" \
  --data-urlencode "from_name=Sinclair Patterns" \
  --data-urlencode "from_email=hello@sinclairpatterns.com" \
  --data-urlencode "reply_to=hello@sinclairpatterns.com" \
  --data-urlencode "title=New Release - [Pattern] [Type] E1 ([Month Year])" \
  --data-urlencode "subject=New Release: [Pattern] [type] - Special launch price $[price]" \
  --data-urlencode "html_text=$HTML" \
  -d "list_ids=zDOpr87Nl7Wztkn2UnQRBg,olrPdvDTCPfq892TwO26oWUw,IHuKbEWHj5pcUcKTqA88Pg" \
  -d "brand_id=1" \
  -d "track_opens=2" \
  -d "track_clicks=2" \
  -d "send_campaign=0"
```

`send_campaign=0` saves as draft. Change to `1` to send immediately.

---

## Checklist Before Uploading

- [ ] All images uploaded to S3 and accessible via CloudFront
- [ ] Campaign ID set (e.g. `helen_e1`)
- [ ] Special price and end date correct
- [ ] No em dashes anywhere (use `-` or restructure)
- [ ] No "flattering/flatter" - describe design instead
- [ ] Pattern short name correct in header (e.g. "Helen pull on pants")
- [ ] Inseam measurements included with Petite/Regular/Tall breakdown
- [ ] Tester quotes proofread
- [ ] Weekly specials prices correct
- [ ] Unsubscribe uses `[unsubscribe]` Sendy tag
- [ ] Upload to Sendy as draft and review before sending
