# New Release Email Templates

## Overview

Three-email sequence for new pattern releases. Each email builds on the previous one, with 2 weekly specials featured at the bottom.

## Templates

### E1 - Introduction & Welcome
**File:** `NewRelease_E1_Template.html`
**Purpose:** Introduce the new pattern with excitement and detail
**Sent:** Day 1 of release

**Key Features:**
- Main header: "NEW PATTERN RELEASE: [PATTERN_NAME]"
- Large hero image
- Full pattern description and introduction
- Complete pattern options list
- Special launch price announcement
- Additional product images
- 2 weekly specials at bottom
- Amazon orange CTA buttons

### E2 - More Details & Images
**File:** `NewRelease_E2_Template.html`
**Purpose:** Provide more lifestyle images and reinforce value
**Sent:** Day 3-4 of release

**Key Features:**
- Header: "[PATTERN_NAME] - MORE DETAILS"
- Different hero image (shows pattern in different fabric/color)
- More detailed description/use cases
- Gallery of additional lifestyle images
- Special price reminder
- 2 weekly specials at bottom
- Amazon orange CTA buttons

### E3 - Last Chance (Urgent)
**File:** `NewRelease_E3_Template.html`
**Purpose:** Create urgency for special pricing ending
**Sent:** Day before special price ends

**Key Features:**
- **RED urgent header:** "LAST CHANCE - SPECIAL PRICE ENDS [DATE]"
- Pattern name header (charcoal gray)
- Hero image
- Short, urgent copy
- Prominent price comparison (special vs regular)
- Larger, bolder CTA button
- Optional quick feature highlights
- 2 weekly specials at bottom

## Placeholders to Replace

### Common to All Templates

```
{{PREHEADER_TEXT}} - Hidden preview text (e.g., "New: Libby Princess Seams Raglan Top")
{{PATTERN_NAME}} - Pattern name (e.g., "Libby")
{{PRODUCT_URL}} - Full Shopify product URL
{{SPECIAL_PRICE}} - Sale price (e.g., "$7.99")
{{SPECIAL_VALID_UNTIL}} - End date text (e.g., "Special price valid until November 9th, 2025")
{{CAMPAIGN_ID}} - Campaign identifier for tracking (e.g., "libby_e1", "libby_e2", "libby_e3")
{{WEEKLY_SPECIALS_SECTION}} - HTML for 2 weekly special patterns (copy from weekly specials template)
```

### E1 Specific

```
{{HERO_IMAGE_URL}} - Main product image URL (CloudFront)
{{INTRO_TEXT}} - Full introduction text with <p> tags and formatting
{{PATTERN_OPTIONS}} - HTML list of pattern options with <br> tags
{{ADDITIONAL_IMAGES}} - HTML for 3-5 additional product images stacked vertically
```

### E2 Specific

```
{{HERO_IMAGE_2_URL}} - Different hero image (show different fabric/styling)
{{DETAILED_TEXT}} - More detailed description, use cases, styling suggestions
{{PATTERN_OPTIONS}} - Same or expanded pattern options
{{GALLERY_IMAGES}} - HTML for 4-6 lifestyle/detail images in gallery format
```

### E3 Specific

```
{{END_DATE}} - Urgent end date (e.g., "TONIGHT", "SUNDAY", "NOVEMBER 9TH")
{{HERO_IMAGE_3_URL}} - Hero image (can reuse from E1 or E2)
{{SHORT_TEXT}} - Brief, urgent reminder text (2-3 sentences max)
{{REGULAR_PRICE}} - Regular/non-sale price (e.g., "$10.99")
{{FEATURE_HIGHLIGHTS}} - (Optional) Quick bullet list of key features
```

## Image Requirements

### Image Locations
- Upload all pattern images to: `s3://sinclairpatterns/MAIL/patterns/[PatternName]/`
- Use CloudFront URLs in templates: `https://d2ukt8mr71y5lh.cloudfront.net/MAIL/patterns/[PatternName]/[filename].jpg`

### Recommended Images

**E1 Images:**
- `hero_e1.jpg` - Main square or portrait product shot
- `detail_1.jpg` - Close-up of special features
- `detail_2.jpg` - Different angle/view
- `detail_3.jpg` - Styling variation
- `lifestyle_1.jpg` - Pattern worn/in use

**E2 Images:**
- `hero_e2.jpg` - Different fabric/color than E1
- `lifestyle_2.jpg` - Different styling
- `lifestyle_3.jpg` - Detail shot
- `colorblock_example.jpg` - If applicable
- `fabric_suggestion.jpg` - Pattern in different fabric weight

**E3 Images:**
- Can reuse `hero_e1.jpg` or `hero_e2.jpg`

### Image Specs
- Format: JPG
- Max width: 1200px
- Optimize for web (< 300KB per image)
- Use descriptive filenames

## Weekly Specials Section

At the bottom of each email, include 2 weekly special patterns using the same format as the weekly specials newsletter:

```html
<!-- Pattern Header -->
<tr>
	<td style="padding: 20px 0 0 0; text-align: center;" valign="middle">
		<div style="padding: 18px; text-align: center; background: linear-gradient(135deg, #4a5568 0%, #2d3748 100%);">
			<h3 style="color: #ffffff; margin: 0; font-size: 18px;">This Week's Special: [Pattern Name]</h3>
		</div>
	</td>
</tr>

<!-- Pattern Image -->
<tr>
	<td align="center" style="padding: 10px;" valign="top">
		<a href="[product_url]" target="_blank">
			<img alt="[Pattern Name]" border="0" class="fluid" src="[image_url]" style="width:100%; max-width:580px; height:auto; display:block;" />
		</a>
	</td>
</tr>

<!-- Pattern Info -->
<tr>
	<td style="padding: 10px; text-align: center;">
		<strong style="font-size: 16px;">[Pattern Name]</strong><br/>
		<span style="color: #9ca3af; text-decoration: line-through;">$[regular_price]</span>
		<span style="color: #c2410c; font-weight: 700; font-size: 20px; margin-left: 6px;">$[sale_price]</span>
	</td>
</tr>

<!-- Short Description -->
<tr>
	<td style="padding: 20px 30px; text-align: left; font-size: 14px; line-height: 22px; color: #4a4a4a;">
		[Brief description]
	</td>
</tr>

<!-- CTA Button -->
<tr>
	<td style="text-align: center; padding: 25px 20px;">
		<table align="center" border="0" cellpadding="0" cellspacing="0" style="margin: auto">
			<tbody>
				<tr>
					<td class="button-td" style="border-radius: 12px; background: #ff9900; box-shadow: 0 4px 12px rgba(255, 153, 0, 0.3); text-align: center;">
						<a class="button-a" href="[product_url]" target="_blank" style="background: #ff9900; border: 16px solid #ff9900; padding: 0 20px; color: #ffffff; font-family: 'Outfit', 'Inter', sans-serif; font-size: 15px; line-height: 1.4; text-align: center; text-decoration: none; display: block; border-radius: 12px; font-weight: 500;">Shop [Pattern] at sinclairpatterns.com</a>
					</td>
				</tr>
			</tbody>
		</table>
	</td>
</tr>
```

Repeat this section twice for 2 different weekly specials.

## Color Scheme

**Background:** `#f7f7f7` (light neutral gray)
**Main Text:** `#4a4a4a` (medium gray)
**Headings:** `#1a202c` (deep charcoal)
**Links:** `#666666` (neutral gray)

**Headers:**
- Main header: `#2d3748` to `#1a202c` gradient (dark charcoal)
- Pattern headers: `#4a5568` to `#2d3748` gradient (slate gray)
- E3 urgent header: `#ff6b6b` to `#ee5a6f` gradient (coral red)

**Buttons:**
- Primary: `#ff9900` (Amazon orange)
- Hover: `#e67e22` (darker orange)

## Typography

- **Body Font:** Inter (via Google Fonts)
- **Heading Font:** Outfit (via Google Fonts)
- **Fallbacks:** -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif

## Email Sending Schedule

**Recommended Timeline:**

| Day | Email | Subject Line Example |
|-----|-------|---------------------|
| 1 | E1 | "New Release: [Pattern Name] - Special Launch Price $X.XX" |
| 3-4 | E2 | "[Pattern Name] - More Details & Styling Ideas" |
| 6-7 | E3 | "Last Chance: [Pattern Name] Special Price Ends Tonight!" |

## Testing Checklist

Before sending:
- [ ] All {{placeholders}} replaced
- [ ] All images uploaded to S3 and accessible via CloudFront
- [ ] All product URLs tested and working
- [ ] Campaign IDs updated (e1, e2, e3)
- [ ] Special price dates correct
- [ ] Weekly specials section populated with current specials
- [ ] Preview text (preheader) set
- [ ] Test send to verify formatting in Gmail, Outlook, Apple Mail
- [ ] Mobile responsive check
- [ ] All links have utm_campaign tracking

## Notes

- These templates use the same modern styling as the weekly specials newsletter
- Neutral gray color scheme won't clash with any pattern photos
- Amazon orange buttons create strong calls-to-action
- E3 uses urgency tactics (red header, countdown language, larger pricing display)
- All templates are mobile-responsive
- Fonts load from Google Fonts with fallbacks for email clients that block external fonts
