"""
Fetch pattern tester testimonials from Sinclair Portal database.
Used for creating newsletter campaigns.
"""

import psycopg2
import json
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Get database connection from environment"""
    conn_string = os.getenv('DATABASE_SINCLAIRPORTAL_DATA')
    return psycopg2.connect(conn_string)

def fetch_testimonials(pattern_slug):
    """
    Fetch testimonials for a specific pattern from the database.

    Args:
        pattern_slug (str): The slug of the pattern (e.g., 'fiona-woven-blouse')

    Returns:
        list: List of dictionaries containing tester data
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
        return []

    project_id, project_name = project
    print(f"Found project: {project_name} (ID: {project_id})")

    # Get the final survey step ID (we know it's step 49 for Fiona, but let's find it dynamically)
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
        return []

    step_id, step_name = step_result
    print(f"Found survey step: {step_name} (ID: {step_id})")

    # Fetch all completed progress entries with testimonials
    cur.execute("""
        SELECT
            m.name,
            m.preferred_name,
            m.instagram_handle,
            p.metadata,
            a.id as application_id
        FROM testers_progress p
        JOIN testers_application a ON p.application_id = a.id
        JOIN testers_member m ON a.tester_id = m.id
        WHERE p.step_id = %s
        AND p.completed = true
        AND p.metadata IS NOT NULL;
    """, (step_id,))

    results = []
    for row in cur.fetchall():
        name, preferred_name, instagram_handle, metadata, app_id = row

        # Metadata structure: metadata['fields'] contains all form responses
        fields = metadata.get('fields', {})

        # Extract testimonial and consent from fields
        social_media_quote = fields.get('social_media_quote', '').strip()
        instagram_permission = fields.get('instagram_feature_permission', '')

        # Check if they want to be tagged
        wants_instagram_tag = 'Yes' in instagram_permission

        # Skip if no quote provided
        if not social_media_quote:
            continue

        # Use preferred name if available, otherwise use full name
        display_name = preferred_name if preferred_name else name

        results.append({
            'name': display_name,
            'instagram_handle': instagram_handle if instagram_handle else '',
            'quote': social_media_quote,
            'wants_instagram_tag': wants_instagram_tag,
            'application_id': app_id,
            'metadata': metadata  # Include full metadata for image access
        })

    cur.close()
    conn.close()

    return results

def format_for_newsletter(testimonials, max_count=5):
    """
    Format testimonials for newsletter use.

    Args:
        testimonials (list): List of testimonial dictionaries
        max_count (int): Maximum number of testimonials to return

    Returns:
        str: Formatted testimonials ready for newsletter
    """
    if not testimonials:
        return "No testimonials found"

    # Take only the first max_count
    selected = testimonials[:max_count]

    formatted = []
    for t in selected:
        name = t['name']
        handle = f"(@{t['instagram_handle']})" if t['instagram_handle'] and t['wants_instagram_tag'] else ""
        quote = t['quote']

        # Format as: Name (@handle): "Quote"
        if handle:
            formatted.append(f'{name} {handle}: "{quote}"')
        else:
            formatted.append(f'{name}: "{quote}"')

    return formatted

def get_tester_images(pattern_slug, application_id):
    """
    Get images submitted by a specific tester for their final submission.

    Args:
        pattern_slug (str): The slug of the pattern
        application_id (int): The application ID of the tester

    Returns:
        list: List of image URLs
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # This would fetch images from testers_postimage or similar
    # Need to understand the image storage structure better
    # Placeholder for now

    cur.close()
    conn.close()

    return []

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python fetch_pattern_testimonials.py <pattern-slug>")
        print("Example: python fetch_pattern_testimonials.py fiona-woven-blouse")
        sys.exit(1)

    pattern_slug = sys.argv[1]

    print(f"\nFetching testimonials for: {pattern_slug}\n")
    testimonials = fetch_testimonials(pattern_slug)

    if testimonials:
        print(f"\nFound {len(testimonials)} testimonials:\n")
        formatted = format_for_newsletter(testimonials)
        for i, t in enumerate(formatted, 1):
            print(f"{i}. {t}\n")
    else:
        print("No testimonials found")
