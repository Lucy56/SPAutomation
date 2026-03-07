"""
Analyze pattern tester feedback to generate insights for newsletter creation.
Extracts key information from all submissions to help write compelling copy.
"""

import psycopg2
import json
import os
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Get database connection from environment"""
    conn_string = os.getenv('DATABASE_SINCLAIRPORTAL_DATA')
    return psycopg2.connect(conn_string)

def analyze_pattern_feedback(pattern_slug):
    """
    Analyze all tester feedback for a pattern to extract newsletter insights.

    Args:
        pattern_slug (str): The slug of the pattern (e.g., 'fiona-woven-blouse')

    Returns:
        dict: Analysis results with insights for newsletter
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Get project ID
    cur.execute("""
        SELECT id, name
        FROM testers_project
        WHERE slug = %s;
    """, (pattern_slug,))

    project = cur.fetchone()
    if not project:
        print(f"Project '{pattern_slug}' not found")
        return {}

    project_id, project_name = project
    print(f"Analyzing: {project_name} (ID: {project_id})\n")

    # Get the final survey step ID
    cur.execute("""
        SELECT id, name
        FROM testers_projectstep
        WHERE project_id = %s
        AND (slug LIKE '%%final%%' OR name LIKE '%%final%%')
        AND submission_config IS NOT NULL
        ORDER BY "order" DESC
        LIMIT 1;
    """, (project_id,))

    step_result = cur.fetchone()
    if not step_result:
        print("No final survey step found")
        return {}

    step_id, step_name = step_result

    # Fetch all completed submissions
    cur.execute("""
        SELECT
            m.name,
            m.preferred_name,
            m.instagram_handle,
            p.metadata
        FROM testers_progress p
        JOIN testers_application a ON p.application_id = a.id
        JOIN testers_member m ON a.tester_id = m.id
        WHERE p.step_id = %s
        AND p.completed = true
        AND p.metadata IS NOT NULL;
    """, (step_id,))

    results = cur.fetchall()
    cur.close()
    conn.close()

    if not results:
        print("No completed submissions found")
        return {}

    # Analyze all submissions
    analysis = {
        'total_submissions': len(results),
        'pattern_options': Counter(),
        'fabrics_used': [],
        'time_taken': Counter(),
        'sizes_made': Counter(),
        'height_options': Counter(),
        'alterations': [],
        'fit_ratings': [],
        'design_ratings': [],
        'positive_feedback': [],
        'negative_feedback': [],
        'technical_highlights': [],
        'sewing_experience': [],
        'recommended_for': [],
    }

    for row in results:
        name, preferred_name, instagram_handle, metadata = row
        fields = metadata.get('fields', {})

        # Pattern options made
        option = fields.get('pattern_option', '')
        if option:
            analysis['pattern_options'][option.lower()] += 1

        # Fabrics used
        fabric = fields.get('fabric_used', '')
        if fabric:
            analysis['fabrics_used'].append(fabric)

        # Time taken
        time = fields.get('time_taken', '')
        if time:
            analysis['time_taken'][time] += 1

        # Sizes
        size = fields.get('chosen_size', '')
        if size:
            analysis['sizes_made'][size.strip()] += 1

        # Height options
        height = fields.get('height_option', '')
        if height:
            analysis['height_options'][height] += 1

        # Alterations
        alterations = fields.get('alterations', '')
        if alterations and alterations.lower() not in ['none', 'n/a', 'no']:
            analysis['alterations'].append(alterations)

        # Ratings (convert to int)
        fit_rating = fields.get('fit_rating', '')
        if fit_rating:
            try:
                analysis['fit_ratings'].append(int(fit_rating))
            except:
                pass

        design_rating = fields.get('design_rating', '')
        if design_rating:
            try:
                analysis['design_ratings'].append(int(design_rating))
            except:
                pass

        # Qualitative feedback
        positive = fields.get('positive_reactions', '')
        if positive and positive.lower() not in ['no', 'n/a', 'none']:
            analysis['positive_feedback'].append(positive)

        negative = fields.get('negative_reactions', '')
        if negative and negative.lower() not in ['no', 'n/a', 'none']:
            analysis['negative_feedback'].append(negative)

        # Comments for insights
        sewing_comments = fields.get('sewing_comments', '')
        if sewing_comments:
            analysis['sewing_experience'].append(sewing_comments)

        design_comments = fields.get('design_comments', '')
        if design_comments:
            analysis['technical_highlights'].append(design_comments)

    return analysis

def generate_newsletter_insights(analysis):
    """
    Generate insights formatted for newsletter creation.

    Args:
        analysis (dict): Analysis results from analyze_pattern_feedback

    Returns:
        str: Formatted insights for newsletter
    """
    if not analysis:
        return "No data available"

    insights = []
    insights.append("=" * 80)
    insights.append("NEWSLETTER INSIGHTS")
    insights.append("=" * 80)
    insights.append(f"\nTotal Testers: {analysis['total_submissions']}\n")

    # Most popular options
    if analysis['pattern_options']:
        insights.append("MOST POPULAR OPTIONS:")
        for option, count in analysis['pattern_options'].most_common(5):
            insights.append(f"  • {option.title()}: {count} testers")
        insights.append("")

    # Sewing time
    if analysis['time_taken']:
        insights.append("SEWING TIME:")
        for time, count in analysis['time_taken'].most_common():
            insights.append(f"  • {time}: {count} testers")
        insights.append("")

    # Height distribution
    if analysis['height_options']:
        insights.append("HEIGHT OPTIONS:")
        for height, count in analysis['height_options'].most_common():
            insights.append(f"  • {height}: {count} testers")
        insights.append("")

    # Average ratings
    if analysis['fit_ratings']:
        avg_fit = sum(analysis['fit_ratings']) / len(analysis['fit_ratings'])
        insights.append(f"AVERAGE FIT RATING: {avg_fit:.1f}/5 ({len(analysis['fit_ratings'])} responses)")

    if analysis['design_ratings']:
        avg_design = sum(analysis['design_ratings']) / len(analysis['design_ratings'])
        insights.append(f"AVERAGE DESIGN RATING: {avg_design:.1f}/5 ({len(analysis['design_ratings'])} responses)")

    insights.append("")

    # Common fabrics
    if analysis['fabrics_used']:
        insights.append("FABRICS USED (sample):")
        for i, fabric in enumerate(analysis['fabrics_used'][:5], 1):
            insights.append(f"  {i}. {fabric[:100]}...")
        insights.append("")

    # Key positive feedback themes
    if analysis['positive_feedback']:
        insights.append("POSITIVE FEEDBACK THEMES:")
        for i, feedback in enumerate(analysis['positive_feedback'][:5], 1):
            insights.append(f"  {i}. {feedback[:150]}...")
        insights.append("")

    # Technical highlights from comments
    if analysis['technical_highlights']:
        insights.append("TECHNICAL HIGHLIGHTS (from design comments):")
        for i, comment in enumerate(analysis['technical_highlights'][:5], 1):
            insights.append(f"  {i}. {comment[:150]}...")
        insights.append("")

    # Sewing experience insights
    if analysis['sewing_experience']:
        insights.append("SEWING EXPERIENCE (from comments):")
        for i, comment in enumerate(analysis['sewing_experience'][:5], 1):
            insights.append(f"  {i}. {comment[:150]}...")
        insights.append("")

    # Alterations needed
    if analysis['alterations']:
        insights.append(f"ALTERATIONS MADE: {len(analysis['alterations'])} testers made adjustments")
        insights.append("(Most testers sewed without alterations)")
        insights.append("")

    # Negative feedback (important to know)
    if analysis['negative_feedback']:
        insights.append("AREAS FOR IMPROVEMENT (negative feedback):")
        for i, feedback in enumerate(analysis['negative_feedback'][:3], 1):
            insights.append(f"  {i}. {feedback[:150]}...")
        insights.append("")

    insights.append("=" * 80)
    insights.append("NEWSLETTER WRITING TIPS:")
    insights.append("=" * 80)

    # Generate specific newsletter tips based on data
    tips = []

    if analysis['time_taken']:
        most_common_time = analysis['time_taken'].most_common(1)[0][0]
        tips.append(f"✓ Mention sewing time: Most testers completed in {most_common_time}")

    if analysis['fit_ratings']:
        avg_fit = sum(analysis['fit_ratings']) / len(analysis['fit_ratings'])
        if avg_fit >= 4.5:
            tips.append(f"✓ Emphasize excellent fit (avg {avg_fit:.1f}/5 rating)")

    if analysis['pattern_options']:
        top_option = analysis['pattern_options'].most_common(1)[0][0]
        tips.append(f"✓ Highlight popular option: {top_option.title()}")

    if len(analysis['alterations']) < analysis['total_submissions'] * 0.3:
        tips.append("✓ Mention that most testers sewed without alterations")

    for tip in tips:
        insights.append(tip)

    insights.append("")

    return "\n".join(insights)

def generate_marketing_copy(analysis, pattern_name="this pattern"):
    """
    Transform analysis data into marketing copy for newsletters.

    Args:
        analysis (dict): Analysis results from analyze_pattern_feedback
        pattern_name (str): Name of the pattern for personalized copy

    Returns:
        dict: Marketing copy snippets for different newsletter sections
    """
    if not analysis:
        return {}

    copy = {
        'headline_options': [],
        'key_features': [],
        'what_testers_loved': [],
        'sewing_experience': [],
        'versatility': [],
        'time_commitment': '',
        'fit_appeal': '',
    }

    # Sewing time marketing copy
    if analysis['time_taken']:
        most_common = analysis['time_taken'].most_common(1)[0][0]
        if '1-3 hours' in most_common or '3-5 hours' in most_common:
            copy['time_commitment'] = "A quick and satisfying sew that comes together in an afternoon."
        elif 'Less than 1 hour' in most_common:
            copy['time_commitment'] = "Fast and easy - you'll have a finished top in under an hour."
        elif '5-8 hours' in most_common:
            copy['time_commitment'] = "A rewarding weekend project with beautiful results."

    # Fit appeal based on ratings
    if analysis['fit_ratings']:
        avg_fit = sum(analysis['fit_ratings']) / len(analysis['fit_ratings'])
        if avg_fit >= 4.5:
            copy['fit_appeal'] = "Pattern testers raved about the fit - with an average rating of {:.1f}/5.".format(avg_fit)
        elif avg_fit >= 4.0:
            copy['fit_appeal'] = "Great fit straight out of the pattern."

    # Extract key themes from positive feedback
    if analysis['positive_feedback']:
        themes = []
        for feedback in analysis['positive_feedback']:
            feedback_lower = feedback.lower()
            if 'french seam' in feedback_lower:
                themes.append('french_seams')
            if 'professional' in feedback_lower or 'clean' in feedback_lower:
                themes.append('professional_finish')
            if 'easy' in feedback_lower or 'quick' in feedback_lower:
                themes.append('easy_sew')
            if 'dart' in feedback_lower:
                themes.append('darts')

        # Count theme frequency
        theme_counts = Counter(themes)
        if theme_counts.get('french_seams', 0) >= 3:
            copy['what_testers_loved'].append("French seams throughout create a completely clean interior finish")
        if theme_counts.get('professional_finish', 0) >= 3:
            copy['what_testers_loved'].append("Professional results that look as good inside as they do out")
        if theme_counts.get('darts', 0) >= 2:
            copy['what_testers_loved'].append("Precise dart placement for a tailored fit")

    # Analyze sewing experience comments for marketing points
    if analysis['sewing_experience']:
        for comment in analysis['sewing_experience']:
            comment_lower = comment.lower()
            if 'no serger' in comment_lower or 'no overlocker' in comment_lower:
                copy['key_features'].append("No overlocker needed")
            if 'beginner' in comment_lower and ('great' in comment_lower or 'good' in comment_lower):
                copy['sewing_experience'].append("Beginner-friendly with clear instructions")
            if 'enclosed' in comment_lower:
                copy['key_features'].append("All seams beautifully enclosed")

    # Versatility from pattern options
    if analysis['pattern_options']:
        option_types = []
        for option in analysis['pattern_options'].keys():
            if 'flutter' in option:
                option_types.append('flutter sleeves')
            if 'flounce' in option:
                option_types.append('flounce sleeves')
            if 'sleeveless' in option:
                option_types.append('sleeveless')
            if 'long' in option:
                option_types.append('longer length')
            if 'short' in option:
                option_types.append('shorter length')

        unique_options = list(set(option_types))
        if len(unique_options) >= 3:
            copy['versatility'].append(f"Multiple options mean endless variations: {', '.join(unique_options[:3])}")

    # Alterations insight
    if analysis['alterations']:
        alteration_percentage = len(analysis['alterations']) / analysis['total_submissions']
        if alteration_percentage < 0.4:
            copy['fit_appeal'] = copy['fit_appeal'] + " Most testers sewed straight from the pattern without adjustments."

    # Fabric versatility
    if analysis['fabrics_used']:
        fabric_mentions = ' '.join(analysis['fabrics_used']).lower()
        fabric_types = []
        if 'voile' in fabric_mentions:
            fabric_types.append('voile')
        if 'linen' in fabric_mentions:
            fabric_types.append('linen')
        if 'cotton' in fabric_mentions or 'lawn' in fabric_mentions:
            fabric_types.append('cotton lawn')
        if 'rayon' in fabric_mentions or 'viscose' in fabric_mentions:
            fabric_types.append('rayon')

        if fabric_types:
            unique_fabrics = list(set(fabric_types))
            copy['versatility'].append(f"Works beautifully in {', '.join(unique_fabrics[:3])} and more")

    return copy

def format_marketing_copy(copy_dict, pattern_name="this pattern"):
    """
    Format marketing copy dictionary into readable sections.

    Args:
        copy_dict (dict): Marketing copy from generate_marketing_copy
        pattern_name (str): Pattern name

    Returns:
        str: Formatted marketing copy
    """
    output = []
    output.append("=" * 80)
    output.append("MARKETING COPY FOR NEWSLETTER")
    output.append("=" * 80)
    output.append("")

    if copy_dict.get('time_commitment'):
        output.append("SEWING TIME:")
        output.append(f"  {copy_dict['time_commitment']}")
        output.append("")

    if copy_dict.get('fit_appeal'):
        output.append("FIT & SIZING:")
        output.append(f"  {copy_dict['fit_appeal']}")
        output.append("")

    if copy_dict.get('what_testers_loved'):
        output.append("WHAT MAKES IT SPECIAL:")
        for point in copy_dict['what_testers_loved']:
            output.append(f"  • {point}")
        output.append("")

    if copy_dict.get('key_features'):
        output.append("KEY FEATURES TO HIGHLIGHT:")
        for feature in set(copy_dict['key_features']):
            output.append(f"  • {feature}")
        output.append("")

    if copy_dict.get('versatility'):
        output.append("VERSATILITY:")
        for point in copy_dict['versatility']:
            output.append(f"  • {point}")
        output.append("")

    if copy_dict.get('sewing_experience'):
        output.append("SEWING EXPERIENCE:")
        for point in copy_dict['sewing_experience']:
            output.append(f"  • {point}")
        output.append("")

    output.append("=" * 80)
    output.append("SUGGESTED EMAIL INTRO PARAGRAPH:")
    output.append("=" * 80)

    # Generate a sample intro paragraph
    intro_parts = []

    if copy_dict.get('what_testers_loved'):
        intro_parts.append(copy_dict['what_testers_loved'][0])

    if copy_dict.get('fit_appeal'):
        intro_parts.append(copy_dict['fit_appeal'].split('.')[0])

    if copy_dict.get('time_commitment'):
        intro_parts.append(copy_dict['time_commitment'])

    if intro_parts:
        output.append("")
        output.append(f"Meet {pattern_name} - {intro_parts[0].lower()}. {' '.join(intro_parts[1:])}")
        output.append("")

    return "\n".join(output)

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python analyze_pattern_feedback.py <pattern-slug> [pattern-name]")
        print("Example: python analyze_pattern_feedback.py fiona-woven-blouse Fiona")
        sys.exit(1)

    pattern_slug = sys.argv[1]
    pattern_name = sys.argv[2] if len(sys.argv) > 2 else pattern_slug.replace('-', ' ').title()

    analysis = analyze_pattern_feedback(pattern_slug)

    if analysis:
        # Generate raw insights
        insights = generate_newsletter_insights(analysis)
        print(insights)
        print("\n\n")

        # Generate marketing copy
        marketing_copy = generate_marketing_copy(analysis, pattern_name)
        formatted_copy = format_marketing_copy(marketing_copy, pattern_name)
        print(formatted_copy)

        # Save both to files
        output_dir = f"Output/New releases/{pattern_slug.replace('-', ' ').title().replace(' ', '')}"
        try:
            os.makedirs(output_dir, exist_ok=True)

            # Save insights
            with open(f"{output_dir}/{pattern_slug}-insights.txt", 'w') as f:
                f.write(insights)

            # Save marketing copy
            with open(f"{output_dir}/{pattern_slug}-marketing-copy.txt", 'w') as f:
                f.write(formatted_copy)

            print(f"\nFiles saved to: {output_dir}/")
        except Exception as e:
            print(f"\nCouldn't save to file: {e}")
