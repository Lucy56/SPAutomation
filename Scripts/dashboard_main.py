#!/usr/bin/env python3
"""
Sinclair Patterns Analytics Dashboard
Professional e-commerce analytics system
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))
from db_schema import get_db_path

# Page config
st.set_page_config(
    page_title="Sinclair Patterns Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #84a98c;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #a3b18a 0%, #84a98c 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 12px rgba(163, 177, 138, 0.3);
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def load_data():
    """Load data from database with caching"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)

    # Load orders
    orders_df = pd.read_sql_query("""
        SELECT
            order_id,
            created_at,
            customer_id,
            country,
            total_price,
            currency,
            financial_status,
            utm_source,
            utm_medium,
            utm_campaign
        FROM orders
        WHERE financial_status = 'paid'
    """, conn)

    # Load line items
    line_items_df = pd.read_sql_query("""
        SELECT
            order_id,
            product_id,
            product_title,
            quantity,
            price,
            price * quantity as revenue
        FROM line_items
        WHERE price > 0
    """, conn)

    conn.close()

    # Convert dates with error handling
    orders_df['created_at'] = pd.to_datetime(orders_df['created_at'], utc=True, errors='coerce')

    # Remove any rows with invalid dates
    orders_df = orders_df[orders_df['created_at'].notna()]

    # Create date columns
    orders_df['date'] = orders_df['created_at'].dt.date
    orders_df['year_month'] = orders_df['created_at'].dt.to_period('M')

    return orders_df, line_items_df

def main():
    # Sidebar navigation
    st.sidebar.markdown("# 📊 Sinclair Analytics")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Select Dashboard",
        [
            "🎯 Action Recommendations",
            "🏠 Executive Overview",
            "📈 Pattern Performance",
            "🛒 Market Basket",
            "👥 Customer Intelligence",
            "🌍 Geographic Insights",
            "📢 Campaign Performance",
            "✨ Weekly Specials AI"
        ]
    )

    # Load data
    try:
        orders_df, line_items_df = load_data()

        # Sidebar metrics
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📊 Quick Stats")
        st.sidebar.metric("Total Orders", f"{len(orders_df):,}")
        st.sidebar.metric("Products Sold", f"{line_items_df['quantity'].sum():,}")
        st.sidebar.metric("Countries", f"{orders_df['country'].nunique():,}")

        # Route to pages
        if "Action Recommendations" in page:
            show_action_recommendations(orders_df, line_items_df)
        elif "Executive Overview" in page:
            show_executive_overview(orders_df, line_items_df)
        elif "Pattern Performance" in page:
            show_pattern_performance(orders_df, line_items_df)
        elif "Market Basket" in page:
            show_market_basket(orders_df, line_items_df)
        elif "Customer Intelligence" in page:
            show_customer_intelligence(orders_df, line_items_df)
        elif "Geographic Insights" in page:
            show_geographic_insights(orders_df, line_items_df)
        elif "Campaign Performance" in page:
            show_campaign_performance(orders_df, line_items_df)
        elif "Weekly Specials" in page:
            show_weekly_specials_ai(orders_df, line_items_df)

    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.info("Make sure the database has been populated by running fetch_orders_resumable.py")

def show_action_recommendations(orders_df, line_items_df):
    """Actionable recommendations for content and product strategy"""
    st.markdown('<p class="main-header">🎯 This Week\'s Action Plan</p>', unsafe_allow_html=True)
    st.markdown("### Specific tasks you can do right now to grow your business")

    import json
    from datetime import date

    # Load free patterns config to exclude
    free_patterns_file = Path(__file__).parent.parent / 'Docs' / 'free_patterns_config.json'
    free_pattern_keywords = []
    if free_patterns_file.exists():
        with open(free_patterns_file, 'r') as f:
            free_config = json.load(f)
            free_pattern_keywords = [p['name'].lower() for p in free_config.get('free_patterns', [])]

    def is_free_pattern_check(title):
        if pd.isna(title):
            return False
        title_lower = title.lower()
        for keyword in free_pattern_keywords:
            if keyword in title_lower:
                return True
        return False

    # Filter out free patterns by NAME, not just price
    line_items_df['is_free'] = line_items_df['product_title'].apply(is_free_pattern_check)
    paid_items = line_items_df[(line_items_df['price'] > 0) & (~line_items_df['is_free'])]
    merged_df = orders_df.merge(paid_items, on='order_id')

    # Calculate recent performance (last 90 days)
    cutoff = pd.Timestamp.now(tz='UTC') - timedelta(days=90)
    recent_df = merged_df[merged_df['created_at'] >= cutoff]

    # Get pattern stats
    pattern_stats = recent_df.groupby('product_title').agg({
        'quantity': 'sum',
        'revenue': 'sum',
        'order_id': 'nunique'
    }).reset_index()
    pattern_stats.columns = ['product_title', 'recent_units', 'recent_revenue', 'num_orders']
    pattern_stats = pattern_stats.sort_values('recent_units', ascending=False)

    # Calculate momentum
    merged_df['year_month'] = merged_df['created_at'].dt.to_period('M')
    monthly_stats = merged_df.groupby(['product_title', 'year_month']).agg({
        'quantity': 'sum'
    }).reset_index()

    def calc_momentum(product_title):
        product_monthly = monthly_stats[monthly_stats['product_title'] == product_title].sort_values('year_month')
        if len(product_monthly) < 2:
            return 0
        recent_months = product_monthly.tail(3)['quantity'].values
        if len(recent_months) < 2:
            return 0
        recent = recent_months[-1]
        previous_avg = recent_months[:-1].mean()
        if previous_avg == 0:
            return 100 if recent > 0 else 0
        return ((recent - previous_avg) / previous_avg) * 100

    pattern_stats['momentum'] = pattern_stats['product_title'].apply(calc_momentum)

    # Get current month for seasonality
    current_month = datetime.now().month
    season = ""
    if current_month in [12, 1, 2]:
        season = "Winter"
        hemisphere_note = "Winter (Northern) / Summer (Southern)"
    elif current_month in [3, 4, 5]:
        season = "Spring"
        hemisphere_note = "Spring (Northern) / Fall (Southern)"
    elif current_month in [6, 7, 8]:
        season = "Summer"
        hemisphere_note = "Summer (Northern) / Winter (Southern)"
    else:
        season = "Fall"
        hemisphere_note = "Fall (Northern) / Spring (Southern)"

    st.info(f"📅 **Current Season:** {hemisphere_note}")

    # ===== INSTAGRAM RECOMMENDATIONS =====
    st.markdown("---")
    st.markdown("## 📱 Instagram Content Plan (This Week)")

    # Get top 3 rising stars
    rising_stars = pattern_stats[pattern_stats['momentum'] > 20].nlargest(3, 'momentum')

    if len(rising_stars) > 0:
        st.markdown("### 🌟 Post 1-3: Rising Star Patterns")
        st.caption("These patterns are trending up - ride the wave!")

        for i, (idx, row) in enumerate(rising_stars.iterrows()):
            with st.expander(f"📸 Post: {row['product_title'][:50]}", expanded=(i == 0)):
                st.markdown(f"**Pattern:** {row['product_title']}")
                st.markdown(f"**Momentum:** +{row['momentum']:.0f}% growth")
                st.markdown(f"**Recent sales:** {int(row['recent_units'])} units (last 90 days)")

                st.markdown("**Suggested Caption:**")
                st.code(f"""🔥 {row['product_title'].split('(')[0].strip()} is TRENDING!

{int(row['recent_units'])} sewists have made this in the last 3 months and we can see why!

The {row['product_title'].split('(')[0].strip().lower()} is perfect for {season.lower()} weather and works up beautifully in jersey knit.

✂️ Tap the link in bio to get the pattern
💚 Tag us in your makes!

#sewingpattern #sewinglove #diywardrobe #{row['product_title'].split()[0].lower()}pattern
""", language="text")

                st.markdown("**When to post:** Today or tomorrow (capitalize on momentum!)")

    # Best sellers
    st.markdown("---")
    st.markdown("### 📊 Post 4-5: Proven Bestsellers")
    st.caption("Social proof sells - show what others love")

    bestsellers = pattern_stats.head(3)
    for _, row in bestsellers.head(2).iterrows():
        with st.expander(f"📸 Post: {row['product_title'][:50]}"):
            st.markdown(f"**Pattern:** {row['product_title']}")
            st.markdown(f"**Social proof:** {int(row['num_orders'])} orders in 90 days")

            st.markdown("**Suggested Caption:**")
            st.code(f"""Everyone's making the {row['product_title'].split('(')[0].strip()}! ✨

This is one of our most popular patterns for good reason:
✅ Easy to sew
✅ Flattering fit
✅ Endless styling options
✅ Perfect for {season.lower()}

Over {int(row['num_orders'])} sewists have downloaded this pattern in the last 3 months!

🛍 Link in bio to join them
📸 Share your version with #sinclair{row['product_title'].split()[0].lower()}

#sewingpattern #bestsellerpattern #sewersofisnstagram
""", language="text")

    # ===== PINTEREST RECOMMENDATIONS =====
    st.markdown("---")
    st.markdown("## 📌 Pinterest Pinning Priority (This Week)")
    st.caption("Pin these patterns first - they have the highest traffic potential")

    # Combine momentum + sales volume for pin priority
    pattern_stats['pin_priority'] = (pattern_stats['momentum'].clip(lower=0) * 0.3) + (pattern_stats['recent_units'] * 0.7)
    top_pin_priorities = pattern_stats.nlargest(5, 'pin_priority')

    st.markdown("### 🎯 Top 5 Patterns to Pin This Week")

    for rank, (_, row) in enumerate(top_pin_priorities.iterrows(), 1):
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"**{rank}. {row['product_title']}**")
            st.markdown(f"   Momentum: +{row['momentum']:.0f}% | Sales: {int(row['recent_units'])} units")

        with col2:
            priority = "🔴 HIGH" if rank <= 2 else "🟡 MEDIUM"
            st.markdown(f"**{priority}**")

    st.markdown("**Pinterest Pin Tips:**")
    st.markdown("""
    - **Title format:** "{Pattern Name} PDF Sewing Pattern | {Style} | Easy {Garment Type}"
    - **Description:** Include fabric suggestions, skill level, and sizing
    - **Keywords:** Add "PDF sewing pattern", "DIY", "handmade wardrobe", season
    - **Board:** Pin to your "New Patterns" board first, then relevant themed boards
    - **Timing:** Space pins 2-3 days apart (don't pin all at once)
    """)

    # ===== NEXT PATTERN DESIGN RECOMMENDATIONS =====
    st.markdown("---")
    st.markdown("## 🎨 Next Pattern to Design")
    st.caption("Data-driven product development")

    # Analyze pattern types
    def categorize_pattern(title):
        title_lower = title.lower()
        if any(word in title_lower for word in ['dress', 'jumpsuit']):
            return 'Dresses & Jumpsuits'
        elif any(word in title_lower for word in ['top', 'shirt', 'blouse', 'tee', 't-shirt']):
            return 'Tops'
        elif any(word in title_lower for word in ['pant', 'short', 'jogger', 'legging']):
            return 'Bottoms'
        elif any(word in title_lower for word in ['hoodie', 'sweatshirt', 'pullover', 'sweater', 'cardigan', 'jacket']):
            return 'Outerwear'
        elif any(word in title_lower for word in ['skirt']):
            return 'Skirts'
        elif any(word in title_lower for word in ['bra', 'brief', 'underwear', 'bralette']):
            return 'Intimates'
        else:
            return 'Other'

    pattern_stats['category'] = pattern_stats['product_title'].apply(categorize_pattern)

    # Category performance
    category_stats = pattern_stats.groupby('category').agg({
        'recent_units': 'sum',
        'recent_revenue': 'sum',
        'product_title': 'count'
    }).reset_index()
    category_stats.columns = ['category', 'total_units', 'total_revenue', 'num_patterns']
    category_stats['revenue_per_pattern'] = category_stats['total_revenue'] / category_stats['num_patterns']
    category_stats = category_stats.sort_values('revenue_per_pattern', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📊 Category Performance")
        fig_category = px.bar(
            category_stats,
            x='category',
            y='revenue_per_pattern',
            title='Revenue per Pattern by Category',
            labels={'revenue_per_pattern': 'Avg Revenue per Pattern ($)', 'category': 'Category'},
            color='num_patterns',
            color_continuous_scale='Teal'
        )
        st.plotly_chart(fig_category, use_container_width=True)

    with col2:
        st.markdown("### 💡 Design Recommendations")

        # Find underrepresented categories
        top_category = category_stats.iloc[0]
        underdeveloped = category_stats[category_stats['num_patterns'] < 3]

        st.markdown(f"**🏆 Highest Revenue per Pattern:**")
        st.markdown(f"{top_category['category']} (${top_category['revenue_per_pattern']:.0f}/pattern)")

        if len(underdeveloped) > 0:
            st.markdown(f"\n**⚠️ Underdeveloped Categories:**")
            for _, cat in underdeveloped.iterrows():
                st.markdown(f"- {cat['category']} (only {int(cat['num_patterns'])} patterns)")

        st.markdown(f"\n**🎯 Recommendation:**")
        if len(underdeveloped) > 0:
            recommended_category = underdeveloped.iloc[0]['category']
            st.success(f"Design a new **{recommended_category}** pattern")
            st.markdown(f"Why? You only have {int(underdeveloped.iloc[0]['num_patterns'])} pattern(s) in this category but it's generating ${underdeveloped.iloc[0]['total_revenue']:.0f} in revenue!")
        else:
            st.success(f"Design another **{top_category['category']}** pattern")
            st.markdown(f"Why? This category earns ${top_category['revenue_per_pattern']:.0f} per pattern - your best ROI!")

    # Specific next pattern suggestion
    st.markdown("---")
    st.markdown("### 🎨 Specific Pattern Suggestion")

    # Market basket analysis to find gaps
    multi_order_items = paid_items.groupby('order_id').filter(lambda x: len(x) > 1)

    # Get most common pattern types from bestsellers
    top_5_patterns = pattern_stats.head(5)['product_title'].tolist()

    st.markdown("**Based on your top sellers and category gaps:**")

    suggestion_box = st.container()
    with suggestion_box:
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            st.markdown("### 💎 Next Pattern Recommendation")

            # Logic for suggestion
            if len(underdeveloped) > 0:
                suggested_cat = underdeveloped.iloc[0]['category']
                if suggested_cat == 'Bottoms':
                    suggestion = "High-waisted Wide Leg Pants"
                    reason = "Your customers buy lots of tops but need bottoms to complete outfits"
                elif suggested_cat == 'Skirts':
                    suggestion = "Midi Skirt with Pockets"
                    reason = "Skirts are underrepresented but complement your popular tops"
                elif suggested_cat == 'Dresses & Jumpsuits':
                    suggestion = f"Casual {season} Dress with Sleeves"
                    reason = f"Fill the dress gap with a versatile {season} option"
                else:
                    suggestion = f"{suggested_cat} Pattern"
                    reason = "Fill the gap in this underserved category"
            else:
                # Suggest based on season
                if season == "Winter":
                    suggestion = "Cozy Oversized Hoodie or Cardigan"
                elif season == "Summer":
                    suggestion = "Lightweight Tank Top or Summer Dress"
                elif season == "Spring":
                    suggestion = "Light Jacket or Kimono"
                else:
                    suggestion = "Layering Piece or Vest"
                reason = f"Seasonal timing - {season} patterns sell well right now"

            st.markdown(f"## {suggestion}")
            st.markdown(f"**Why this pattern?**")
            st.info(reason)

            st.markdown("**Quick validation:**")
            st.markdown(f"- ✅ Check Pinterest for '{suggestion}' search volume")
            st.markdown(f"- ✅ Look at competitor patterns in this style")
            st.markdown(f"- ✅ Survey your Facebook group for interest")

    # ===== EXPORT FOR AUTOMATION =====
    st.markdown("---")
    st.markdown("## 📤 Export for Automation")
    st.caption("Download ready-to-use content for scheduling tools")

    if st.button("🎬 Generate Content Export", type="primary"):
        # Prepare Instagram posts
        instagram_posts = []

        # Rising stars posts
        for _, row in rising_stars.iterrows():
            instagram_posts.append({
                'post_type': 'rising_star',
                'pattern': row['product_title'],
                'caption': f"""🔥 {row['product_title'].split('(')[0].strip()} is TRENDING!

{int(row['recent_units'])} sewists have made this in the last 3 months and we can see why!

The {row['product_title'].split('(')[0].strip().lower()} is perfect for {season.lower()} weather and works up beautifully in jersey knit.

✂️ Tap the link in bio to get the pattern
💚 Tag us in your makes!

#sewingpattern #sewinglove #diywardrobe #{row['product_title'].split()[0].lower()}pattern""",
                'hashtags': f"#sewingpattern #sewinglove #diywardrobe #{row['product_title'].split()[0].lower()}pattern",
                'momentum': f"+{row['momentum']:.0f}%",
                'suggested_day': 'Today'
            })

        # Bestseller posts
        for i, (_, row) in enumerate(bestsellers.head(2).iterrows()):
            instagram_posts.append({
                'post_type': 'bestseller',
                'pattern': row['product_title'],
                'caption': f"""Everyone's making the {row['product_title'].split('(')[0].strip()}! ✨

This is one of our most popular patterns for good reason:
✅ Easy to sew
✅ Flattering fit
✅ Endless styling options
✅ Perfect for {season.lower()}

Over {int(row['num_orders'])} sewists have downloaded this pattern in the last 3 months!

🛍 Link in bio to join them
📸 Share your version with #sinclair{row['product_title'].split()[0].lower()}

#sewingpattern #bestsellerpattern #sewersofisnstagram""",
                'hashtags': f"#sewingpattern #bestsellerpattern #sewersofisnstagram #sinclair{row['product_title'].split()[0].lower()}",
                'social_proof': f"{int(row['num_orders'])} orders",
                'suggested_day': f"Day {i+3}"
            })

        # Pinterest pins
        pinterest_pins = []
        for rank, (_, row) in enumerate(top_pin_priorities.iterrows(), 1):
            pattern_name = row['product_title'].split('(')[0].strip()
            pinterest_pins.append({
                'priority': rank,
                'pattern': row['product_title'],
                'title': f"{pattern_name} PDF Sewing Pattern | Easy DIY | Instant Download",
                'description': f"Make your own {pattern_name.lower()}! This PDF sewing pattern includes step-by-step instructions, sizing guide, and printable pattern pieces. Perfect for {season.lower()} sewing projects. Digital download, instant access. #PDFSewingPattern #DIY #Handmade",
                'keywords': f"PDF sewing pattern, {pattern_name.lower()}, DIY clothing, handmade wardrobe, {season.lower()} sewing",
                'board': "New Patterns",
                'momentum': f"+{row['momentum']:.0f}%",
                'sales': int(row['recent_units'])
            })

        # Create export data
        export_data = {
            'generated_date': datetime.now().strftime('%Y-%m-%d'),
            'season': season,
            'instagram_posts': instagram_posts,
            'pinterest_pins': pinterest_pins,
            'next_pattern_design': {
                'suggestion': suggestion,
                'reason': reason,
                'category': suggested_cat if len(underdeveloped) > 0 else top_category['category']
            }
        }

        # Display JSON
        st.json(export_data)

        # Create download button
        import json
        json_str = json.dumps(export_data, indent=2)

        st.download_button(
            label="📥 Download JSON (for automation scripts)",
            data=json_str,
            file_name=f"content_plan_{datetime.now().strftime('%Y-%m-%d')}.json",
            mime="application/json"
        )

        # Create CSV for Instagram
        import io
        instagram_csv = io.StringIO()
        instagram_csv.write("Post Type,Pattern,Caption,Hashtags,Suggested Day\n")
        for post in instagram_posts:
            caption_clean = post['caption'].replace('\n', ' ').replace('"', '""')
            instagram_csv.write(f'"{post["post_type"]}","{post["pattern"]}","{caption_clean}","{post["hashtags"]}","{post["suggested_day"]}"\n')

        st.download_button(
            label="📥 Download Instagram Posts (CSV)",
            data=instagram_csv.getvalue(),
            file_name=f"instagram_posts_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )

        # Create CSV for Pinterest
        pinterest_csv = io.StringIO()
        pinterest_csv.write("Priority,Pattern,Title,Description,Keywords,Board\n")
        for pin in pinterest_pins:
            desc_clean = pin['description'].replace('\n', ' ').replace('"', '""')
            pinterest_csv.write(f'{pin["priority"]},"{pin["pattern"]}","{pin["title"]}","{desc_clean}","{pin["keywords"]}","{pin["board"]}"\n')

        st.download_button(
            label="📥 Download Pinterest Pins (CSV)",
            data=pinterest_csv.getvalue(),
            file_name=f"pinterest_pins_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )

        st.success("✅ Content exported! Use these files with Later, Tailwind, Buffer, or custom automation scripts.")

def show_executive_overview(orders_df, line_items_df):
    """Executive dashboard with key metrics"""
    st.markdown('<p class="main-header">🏠 Executive Overview</p>', unsafe_allow_html=True)
    st.markdown("### Business Performance at a Glance")

    # Date filter
    col1, col2 = st.columns([1, 1])
    with col1:
        days_filter = st.selectbox(
            "Time Period",
            [30, 60, 90, 180, 365, "All Time"],
            index=2
        )

    # Filter data
    if days_filter != "All Time":
        cutoff = pd.Timestamp.now(tz='UTC') - timedelta(days=days_filter)
        filtered_orders = orders_df[orders_df['created_at'] >= cutoff]
    else:
        filtered_orders = orders_df

    # Merge for revenue
    merged_df = filtered_orders.merge(line_items_df, on='order_id')

    # Top metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Orders",
            f"{len(filtered_orders):,}",
            delta=f"+{len(filtered_orders)/len(orders_df)*100:.1f}% of all time"
        )

    with col2:
        total_revenue = filtered_orders['total_price'].sum()
        st.metric(
            "Revenue",
            f"${total_revenue:,.0f}",
            delta=f"${total_revenue/len(filtered_orders):.2f} AOV"
        )

    with col3:
        units_sold = merged_df['quantity'].sum()
        st.metric(
            "Units Sold",
            f"{units_sold:,}",
            delta=f"{units_sold/len(filtered_orders):.1f} per order"
        )

    with col4:
        unique_customers = filtered_orders['customer_id'].nunique()
        st.metric(
            "Customers",
            f"{unique_customers:,}",
            delta=f"{len(filtered_orders)/unique_customers:.1f} orders/customer"
        )

    st.markdown("---")

    # Revenue trend
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 📈 Revenue Trend")
        daily_revenue = filtered_orders.groupby('date')['total_price'].sum().reset_index()
        fig = px.line(
            daily_revenue,
            x='date',
            y='total_price',
            title='Daily Revenue',
            labels={'total_price': 'Revenue ($)', 'date': 'Date'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 🏆 Top 10 Patterns")
        top_products = merged_df.groupby('product_title').agg({
            'quantity': 'sum',
            'revenue': 'sum'
        }).sort_values('quantity', ascending=False).head(10)

        for idx, (product, row) in enumerate(top_products.iterrows(), 1):
            st.markdown(f"**{idx}. {product[:40]}...**")
            st.markdown(f"   {int(row['quantity'])} units • ${row['revenue']:,.0f}")

    st.markdown("---")

    # Monthly comparison
    st.markdown("### 📊 Monthly Performance")
    monthly_data = filtered_orders.groupby(filtered_orders['created_at'].dt.to_period('M')).agg({
        'order_id': 'count',
        'total_price': 'sum'
    }).reset_index()
    monthly_data['created_at'] = monthly_data['created_at'].astype(str)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly_data['created_at'],
        y=monthly_data['order_id'],
        name='Orders',
        yaxis='y',
        marker_color='#a3b18a'
    ))
    fig.add_trace(go.Scatter(
        x=monthly_data['created_at'],
        y=monthly_data['total_price'],
        name='Revenue',
        yaxis='y2',
        marker_color='#84a98c',
        line=dict(width=3)
    ))

    fig.update_layout(
        title='Monthly Orders vs Revenue',
        xaxis=dict(title='Month'),
        yaxis=dict(title='Orders', side='left'),
        yaxis2=dict(title='Revenue ($)', overlaying='y', side='right'),
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)

def show_pattern_performance(orders_df, line_items_df):
    """Pattern-level performance analysis"""
    st.markdown('<p class="main-header">📈 Pattern Performance</p>', unsafe_allow_html=True)
    st.markdown("### Deep Dive into Product Lifecycle & Momentum")
    st.info("📌 Analyzing **active patterns only** (sold within last 365 days). Discontinued patterns are automatically excluded.")

    # Merge data
    merged_df = orders_df.merge(line_items_df, on='order_id')

    # Filter controls
    col1, col2 = st.columns([1, 1])
    with col1:
        min_units = st.slider("Minimum units sold (all-time)", 0, 500, 50)
    with col2:
        time_window = st.selectbox("Analysis Window", [30, 60, 90, 180, 365], index=2)

    # Calculate pattern metrics
    cutoff = pd.Timestamp.now(tz='UTC') - timedelta(days=time_window)
    recent_df = merged_df[merged_df['created_at'] >= cutoff]

    # All-time performance
    all_time_stats = merged_df.groupby('product_title').agg({
        'quantity': 'sum',
        'revenue': 'sum',
        'order_id': 'nunique',
        'created_at': ['min', 'max']
    }).reset_index()
    all_time_stats.columns = ['product_title', 'total_units', 'total_revenue', 'total_orders', 'first_sale', 'last_sale']

    # Recent performance
    recent_stats = recent_df.groupby('product_title').agg({
        'quantity': 'sum',
        'revenue': 'sum'
    }).reset_index()
    recent_stats.columns = ['product_title', 'recent_units', 'recent_revenue']

    # Calculate monthly stats for momentum
    merged_df['year_month'] = merged_df['created_at'].dt.to_period('M')
    monthly_stats = merged_df.groupby(['product_title', 'year_month']).agg({
        'quantity': 'sum'
    }).reset_index()

    # Merge stats
    pattern_stats = all_time_stats.merge(recent_stats, on='product_title', how='left')
    pattern_stats['recent_units'] = pattern_stats['recent_units'].fillna(0)
    pattern_stats['recent_revenue'] = pattern_stats['recent_revenue'].fillna(0)

    # Filter by minimum units
    pattern_stats = pattern_stats[pattern_stats['total_units'] >= min_units]

    # Calculate age and velocity
    now = pd.Timestamp.now(tz='UTC')
    pattern_stats['age_days'] = (now - pd.to_datetime(pattern_stats['first_sale'])).dt.days
    pattern_stats['days_since_last_sale'] = (now - pd.to_datetime(pattern_stats['last_sale'])).dt.days
    pattern_stats['velocity_per_month'] = (pattern_stats['total_units'] / pattern_stats['age_days']) * 30
    pattern_stats['avg_revenue_per_unit'] = pattern_stats['total_revenue'] / pattern_stats['total_units']

    # Filter out discontinued patterns (no sales in last 365 days)
    pattern_stats = pattern_stats[pattern_stats['days_since_last_sale'] <= 365]

    # Calculate momentum (3-month trend)
    def calculate_momentum(product_title):
        product_monthly = monthly_stats[monthly_stats['product_title'] == product_title].sort_values('year_month')
        if len(product_monthly) < 2:
            return 0

        recent_months = product_monthly.tail(3)['quantity'].values
        if len(recent_months) < 2:
            return 0

        # Simple momentum: recent month vs previous months average
        if len(recent_months) == 1:
            return 0

        recent = recent_months[-1]
        previous_avg = recent_months[:-1].mean()

        if previous_avg == 0:
            return 100 if recent > 0 else 0

        momentum = ((recent - previous_avg) / previous_avg) * 100
        return momentum

    pattern_stats['momentum'] = pattern_stats['product_title'].apply(calculate_momentum)

    # Classify lifecycle stage
    def classify_lifecycle(row):
        if row['age_days'] < 90:
            return 'Introduction'
        elif row['momentum'] > 20:
            return 'Growth'
        elif row['momentum'] < -20:
            return 'Decline'
        else:
            return 'Maturity'

    pattern_stats['lifecycle_stage'] = pattern_stats.apply(classify_lifecycle, axis=1)

    # Display key metrics
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Patterns Analyzed", len(pattern_stats))
    with col2:
        growing = len(pattern_stats[pattern_stats['lifecycle_stage'] == 'Growth'])
        st.metric("Growing Patterns", growing)
    with col3:
        avg_velocity = pattern_stats['velocity_per_month'].mean()
        st.metric("Avg Velocity", f"{avg_velocity:.1f}/mo")
    with col4:
        hot_products = len(pattern_stats[pattern_stats['momentum'] > 50])
        st.metric("Hot Products", hot_products, delta="Momentum > 50%")

    st.markdown("---")

    # Visualization: Momentum vs Sales
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 📊 Performance Matrix")
        fig = px.scatter(
            pattern_stats.head(50),
            x='velocity_per_month',
            y='momentum',
            size='total_units',
            color='lifecycle_stage',
            hover_data=['product_title', 'total_units', 'recent_units', 'age_days'],
            title='Pattern Performance: Velocity vs Momentum',
            labels={
                'velocity_per_month': 'Velocity (units/month)',
                'momentum': 'Momentum Score (%)',
                'lifecycle_stage': 'Lifecycle Stage'
            },
            color_discrete_map={
                'Introduction': '#ffd166',
                'Growth': '#06ffa5',
                'Maturity': '#4a90e2',
                'Decline': '#ef476f'
            }
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 🎯 Lifecycle Distribution")
        lifecycle_dist = pattern_stats['lifecycle_stage'].value_counts()
        fig_pie = px.pie(
            values=lifecycle_dist.values,
            names=lifecycle_dist.index,
            title='Pattern Stages',
            color=lifecycle_dist.index,
            color_discrete_map={
                'Introduction': '#ffd166',
                'Growth': '#06ffa5',
                'Maturity': '#4a90e2',
                'Decline': '#ef476f'
            }
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # Top movers
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🚀 Top Gainers (Momentum)")
        top_gainers = pattern_stats.nlargest(10, 'momentum')[['product_title', 'momentum', 'recent_units', 'velocity_per_month']]
        for idx, row in top_gainers.iterrows():
            title = row['product_title'][:45]
            st.markdown(f"**{title}**")
            st.markdown(f"   Momentum: {row['momentum']:+.1f}% | Velocity: {row['velocity_per_month']:.1f}/mo | Recent: {int(row['recent_units'])} units")

    with col2:
        st.markdown("### 📉 Slowing Down (Need Boost)")
        st.caption("Active patterns with declining momentum")
        top_decliners = pattern_stats.nsmallest(10, 'momentum')[['product_title', 'momentum', 'days_since_last_sale', 'recent_units', 'total_units']]
        for idx, row in top_decliners.iterrows():
            title = row['product_title'][:45]
            st.markdown(f"**{title}**")
            st.markdown(f"   Momentum: {row['momentum']:+.1f}% | Recent: {int(row['recent_units'])} units | Last sale: {int(row['days_since_last_sale'])} days ago")

    st.markdown("---")

    # Detailed table
    st.markdown("### 📋 Full Pattern Performance Table")

    display_df = pattern_stats[['product_title', 'lifecycle_stage', 'total_units', 'recent_units',
                                  'momentum', 'velocity_per_month', 'avg_revenue_per_unit',
                                  'age_days', 'days_since_last_sale']].sort_values('momentum', ascending=False)

    display_df.columns = ['Pattern', 'Stage', 'Total Units', 'Recent Units',
                          'Momentum %', 'Velocity/Mo', 'Avg $/Unit', 'Age (Days)', 'Days Since Last Sale']

    # Format numeric columns
    display_df['Momentum %'] = display_df['Momentum %'].round(1)
    display_df['Velocity/Mo'] = display_df['Velocity/Mo'].round(1)
    display_df['Avg $/Unit'] = display_df['Avg $/Unit'].round(2)

    st.dataframe(display_df, use_container_width=True, height=400)

def show_market_basket(orders_df, line_items_df):
    """Market basket analysis"""
    st.markdown('<p class="main-header">🛒 Market Basket Analysis</p>', unsafe_allow_html=True)
    st.markdown("### Discover What Patterns Customers Buy Together")

    # Filter controls
    col1, col2 = st.columns([1, 1])
    with col1:
        min_occurrences = st.slider("Minimum co-purchases", 2, 50, 10)
    with col2:
        time_window = st.selectbox("Time Period", [90, 180, 365, "All Time"], index=2)

    # Filter orders by time
    if time_window != "All Time":
        cutoff = pd.Timestamp.now(tz='UTC') - timedelta(days=time_window)
        filtered_orders = orders_df[orders_df['created_at'] >= cutoff]['order_id']
        filtered_items = line_items_df[line_items_df['order_id'].isin(filtered_orders)]
    else:
        filtered_items = line_items_df

    # Find orders with multiple items
    order_counts = filtered_items.groupby('order_id').size()
    multi_item_orders = order_counts[order_counts > 1].index
    multi_items_df = filtered_items[filtered_items['order_id'].isin(multi_item_orders)]

    # Calculate market basket pairs
    st.markdown("---")
    with st.spinner("Analyzing purchase patterns..."):
        # Self-join to find product pairs
        pairs_list = []

        for order_id in multi_items_df['order_id'].unique():
            order_products = multi_items_df[multi_items_df['order_id'] == order_id]['product_title'].unique()

            # Create all pairs
            for i, prod_a in enumerate(order_products):
                for prod_b in order_products[i+1:]:
                    pairs_list.append({
                        'product_a': prod_a,
                        'product_b': prod_b
                    })

        if not pairs_list:
            st.warning("No product pairs found in the selected time period")
            return

        pairs_df = pd.DataFrame(pairs_list)

        # Count occurrences
        pair_counts = pairs_df.groupby(['product_a', 'product_b']).size().reset_index(name='times_together')
        pair_counts = pair_counts[pair_counts['times_together'] >= min_occurrences].sort_values('times_together', ascending=False)

        # Calculate support (how often products appear together)
        total_orders = len(multi_item_orders)
        pair_counts['support'] = (pair_counts['times_together'] / total_orders * 100).round(2)

        # Calculate individual product frequencies for confidence
        product_freq = filtered_items.groupby('product_title')['order_id'].nunique().to_dict()

        def calc_confidence(row):
            freq_a = product_freq.get(row['product_a'], 1)
            return round(row['times_together'] / freq_a * 100, 2)

        pair_counts['confidence_a_to_b'] = pair_counts.apply(calc_confidence, axis=1)

        # Calculate lift
        def calc_lift(row):
            freq_a = product_freq.get(row['product_a'], 1) / total_orders
            freq_b = product_freq.get(row['product_b'], 1) / total_orders
            observed = row['times_together'] / total_orders
            expected = freq_a * freq_b
            return round(observed / expected, 2) if expected > 0 else 0

        pair_counts['lift'] = pair_counts.apply(calc_lift, axis=1)

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Product Pairs Found", len(pair_counts))
    with col2:
        st.metric("Multi-Item Orders", len(multi_item_orders))
    with col3:
        avg_lift = pair_counts['lift'].mean()
        st.metric("Avg Lift Score", f"{avg_lift:.2f}x")
    with col4:
        strong_pairs = len(pair_counts[pair_counts['lift'] > 2])
        st.metric("Strong Associations", strong_pairs, delta="Lift > 2x")

    st.markdown("---")

    # Top 20 pairs visualization
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 🔗 Top 20 Product Associations")
        top_20 = pair_counts.head(20).copy()
        top_20['pair_label'] = top_20['product_a'].str[:25] + ' + ' + top_20['product_b'].str[:25]

        fig = px.bar(
            top_20,
            x='times_together',
            y='pair_label',
            orientation='h',
            color='lift',
            hover_data=['support', 'confidence_a_to_b', 'lift'],
            title='Most Frequently Bought Together',
            labels={
                'times_together': 'Times Bought Together',
                'pair_label': 'Product Pair',
                'lift': 'Lift Score'
            },
            color_continuous_scale='Viridis'
        )
        fig.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 📊 Lift Distribution")
        fig_hist = px.histogram(
            pair_counts,
            x='lift',
            nbins=30,
            title='Association Strength',
            labels={'lift': 'Lift Score', 'count': 'Number of Pairs'}
        )
        fig_hist.add_vline(x=1, line_dash="dash", line_color="red",
                          annotation_text="Random chance", annotation_position="top")
        st.plotly_chart(fig_hist, use_container_width=True)

        st.markdown("### 💡 What is Lift?")
        st.markdown("""
        **Lift Score** measures how much more likely products are bought together vs random chance:
        - **< 1.0**: Less likely than random
        - **= 1.0**: Random association
        - **> 1.0**: Positive association
        - **> 2.0**: Strong association
        - **> 3.0**: Very strong association
        """)

    st.markdown("---")

    # Pattern explorer - select a pattern to see what it's bought with
    st.markdown("### 🔍 Pattern Association Explorer")

    available_patterns = sorted(filtered_items['product_title'].unique())
    selected_pattern = st.selectbox("Select a pattern to see what customers buy with it:", available_patterns)

    if selected_pattern:
        # Find all pairs involving this pattern
        pattern_pairs = pair_counts[
            (pair_counts['product_a'] == selected_pattern) |
            (pair_counts['product_b'] == selected_pattern)
        ].copy()

        # Normalize so selected pattern is always in product_a
        pattern_pairs['companion'] = pattern_pairs.apply(
            lambda row: row['product_b'] if row['product_a'] == selected_pattern else row['product_a'],
            axis=1
        )

        pattern_pairs = pattern_pairs.sort_values('times_together', ascending=False).head(15)

        if len(pattern_pairs) > 0:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"#### Top Companions for: {selected_pattern[:50]}")
                for idx, row in pattern_pairs.iterrows():
                    st.markdown(f"""
                    **{row['companion'][:50]}**
                    - Bought together {int(row['times_together'])} times
                    - Confidence: {row['confidence_a_to_b']:.1f}%
                    - Lift: {row['lift']:.2f}x
                    """)

            with col2:
                fig_companions = px.bar(
                    pattern_pairs,
                    x='times_together',
                    y='companion',
                    orientation='h',
                    color='lift',
                    title='Association Strength',
                    color_continuous_scale='Teal'
                )
                fig_companions.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig_companions, use_container_width=True)
        else:
            st.info("This pattern is typically bought alone or doesn't meet the minimum co-purchase threshold.")

    st.markdown("---")

    # Full data table
    st.markdown("### 📋 All Product Associations")

    display_pairs = pair_counts[['product_a', 'product_b', 'times_together', 'support', 'confidence_a_to_b', 'lift']].copy()
    display_pairs.columns = ['Pattern A', 'Pattern B', 'Co-purchases', 'Support %', 'Confidence %', 'Lift']

    st.dataframe(display_pairs, use_container_width=True, height=400)

def show_customer_intelligence(orders_df, line_items_df):
    """Customer segmentation"""
    st.markdown('<p class="main-header">👥 Customer Intelligence</p>', unsafe_allow_html=True)
    st.markdown("### RFM Analysis & Customer Segmentation")

    # Load free pattern names from config to exclude them
    import json
    free_patterns_file = Path(__file__).parent.parent / 'Docs' / 'free_patterns_config.json'
    free_pattern_keywords = []
    if free_patterns_file.exists():
        with open(free_patterns_file, 'r') as f:
            free_config = json.load(f)
            free_pattern_keywords = [p['name'].lower() for p in free_config.get('free_patterns', [])]

    # Filter out free patterns by name (not just price)
    def is_free_pattern_check(title):
        if pd.isna(title):
            return False
        title_lower = title.lower()
        for keyword in free_pattern_keywords:
            if keyword in title_lower:
                return True
        return False

    line_items_df['is_free'] = line_items_df['product_title'].apply(is_free_pattern_check)
    paid_items = line_items_df[(line_items_df['price'] > 0) & (~line_items_df['is_free'])]

    # Calculate RFM metrics per customer (paid orders only)
    paid_orders_df = orders_df[orders_df['order_id'].isin(paid_items['order_id'])]
    today = pd.Timestamp.now(tz='UTC')

    # Recency: Days since last PAID purchase
    customer_recency = paid_orders_df.groupby('customer_id')['created_at'].max().reset_index()
    customer_recency['recency_days'] = (today - customer_recency['created_at']).dt.days
    customer_recency = customer_recency[['customer_id', 'recency_days']]

    # Frequency: Number of PAID orders
    customer_frequency = paid_orders_df.groupby('customer_id').size().reset_index(name='frequency')

    # Monetary: Total spending (paid only)
    customer_monetary = paid_orders_df.groupby('customer_id')['total_price'].sum().reset_index()
    customer_monetary.columns = ['customer_id', 'monetary_value']

    # Merge RFM data
    rfm = customer_recency.merge(customer_frequency, on='customer_id')
    rfm = rfm.merge(customer_monetary, on='customer_id')

    # Add first PAID purchase date for tenure analysis
    first_purchase = paid_orders_df.groupby('customer_id')['created_at'].min().reset_index()
    first_purchase['tenure_days'] = (today - first_purchase['created_at']).dt.days
    rfm = rfm.merge(first_purchase[['customer_id', 'tenure_days']], on='customer_id')

    # Calculate RFM scores (1-5 scale)
    rfm['r_score'] = pd.qcut(rfm['recency_days'], 5, labels=[5, 4, 3, 2, 1], duplicates='drop')
    rfm['f_score'] = pd.qcut(rfm['frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5], duplicates='drop')
    rfm['m_score'] = pd.qcut(rfm['monetary_value'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5], duplicates='drop')

    # Convert to numeric
    rfm['r_score'] = rfm['r_score'].astype(int)
    rfm['f_score'] = rfm['f_score'].astype(int)
    rfm['m_score'] = rfm['m_score'].astype(int)

    # Calculate RFM total score
    rfm['rfm_score'] = rfm['r_score'] + rfm['f_score'] + rfm['m_score']

    # Segment customers
    def segment_customer(row):
        if row['r_score'] >= 4 and row['f_score'] >= 4 and row['m_score'] >= 4:
            return 'Champions'
        elif row['r_score'] >= 3 and row['f_score'] >= 3:
            return 'Loyal Customers'
        elif row['r_score'] >= 4 and row['f_score'] <= 2:
            return 'New Customers'
        elif row['r_score'] <= 2 and row['f_score'] >= 3:
            return 'At Risk'
        elif row['r_score'] <= 2 and row['f_score'] <= 2:
            return 'Lost'
        elif row['m_score'] >= 4:
            return 'Big Spenders'
        else:
            return 'Promising'

    rfm['segment'] = rfm.apply(segment_customer, axis=1)

    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Customers", f"{len(rfm):,}")
    with col2:
        champions = len(rfm[rfm['segment'] == 'Champions'])
        st.metric("Champions", champions, delta=f"{champions/len(rfm)*100:.1f}%")
    with col3:
        avg_value = rfm['monetary_value'].mean()
        st.metric("Avg Customer Value", f"${avg_value:.2f}")
    with col4:
        at_risk = len(rfm[rfm['segment'] == 'At Risk'])
        st.metric("At Risk", at_risk, delta=f"{at_risk/len(rfm)*100:.1f}%", delta_color="inverse")

    st.markdown("---")

    # Segment distribution
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 📊 Customer Segment Distribution")
        segment_counts = rfm['segment'].value_counts().reset_index()
        segment_counts.columns = ['Segment', 'Count']
        segment_counts['Revenue'] = segment_counts['Segment'].apply(
            lambda s: rfm[rfm['segment'] == s]['monetary_value'].sum()
        )

        fig = px.bar(
            segment_counts,
            x='Segment',
            y='Count',
            color='Revenue',
            title='Customers by Segment',
            labels={'Count': 'Number of Customers', 'Revenue': 'Total Revenue'},
            color_continuous_scale='Greens'
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 🥧 Revenue Share")
        fig_pie = px.pie(
            segment_counts,
            values='Revenue',
            names='Segment',
            title='Revenue by Segment',
            color_discrete_sequence=px.colors.sequential.Teal
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # Segment details
    st.markdown("### 📋 Segment Performance")

    segment_stats = rfm.groupby('segment').agg({
        'customer_id': 'count',
        'recency_days': 'mean',
        'frequency': 'mean',
        'monetary_value': ['mean', 'sum'],
        'tenure_days': 'mean'
    }).reset_index()

    segment_stats.columns = ['Segment', 'Customers', 'Avg Recency (days)', 'Avg Orders',
                             'Avg Value ($)', 'Total Revenue ($)', 'Avg Tenure (days)']

    # Format
    segment_stats['Avg Recency (days)'] = segment_stats['Avg Recency (days)'].round(0).astype(int)
    segment_stats['Avg Orders'] = segment_stats['Avg Orders'].round(1)
    segment_stats['Avg Value ($)'] = segment_stats['Avg Value ($)'].round(2)
    segment_stats['Total Revenue ($)'] = segment_stats['Total Revenue ($)'].round(0).astype(int)
    segment_stats['Avg Tenure (days)'] = segment_stats['Avg Tenure (days)'].round(0).astype(int)

    # Sort by revenue
    segment_stats = segment_stats.sort_values('Total Revenue ($)', ascending=False)

    st.dataframe(segment_stats, use_container_width=True)

    st.markdown("---")

    # RFM Score distribution
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📈 RFM Score Distribution")
        fig_hist = px.histogram(
            rfm,
            x='rfm_score',
            nbins=15,
            title='Customer Distribution by RFM Score',
            labels={'rfm_score': 'RFM Score (3-15)', 'count': 'Number of Customers'},
            color_discrete_sequence=['#84a98c']
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    with col2:
        st.markdown("### 💰 Value vs Frequency")
        sample_rfm = rfm.sample(min(1000, len(rfm)))  # Sample for performance
        fig_scatter = px.scatter(
            sample_rfm,
            x='frequency',
            y='monetary_value',
            color='segment',
            title='Customer Value Analysis',
            labels={'frequency': 'Number of Orders', 'monetary_value': 'Total Spent ($)'},
            hover_data=['recency_days', 'rfm_score']
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    st.markdown("---")

    # FREE-TO-PAID CUSTOMER JOURNEY ANALYSIS
    st.markdown("### 🎁 Free Pattern Acquisition Funnel")
    st.markdown("#### Track customer journey from free patterns to paying customers")

    # Use the already-filtered free patterns from above
    all_items_with_flag = line_items_df.copy()
    free_items = all_items_with_flag[all_items_with_flag['is_free']]
    free_pattern_names = free_items['product_title'].unique()

    st.caption(f"📋 Identified {len(free_pattern_names)} free patterns: {', '.join(list(free_pattern_names)[:5])}{'...' if len(free_pattern_names) > 5 else ''}")
    st.caption(f"Looking for: {', '.join([k.title() for k in free_pattern_keywords])}")

    # Get customers who got free patterns
    free_customers = orders_df[orders_df['order_id'].isin(free_items['order_id'])]['customer_id'].unique()

    # Get all orders for these customers
    free_customer_orders = orders_df[orders_df['customer_id'].isin(free_customers)].copy()
    free_customer_orders = free_customer_orders.sort_values(['customer_id', 'created_at'])

    # Find first order date for each customer
    first_orders = orders_df.groupby('customer_id')['created_at'].min().reset_index()
    first_orders.columns = ['customer_id', 'first_order_date']

    # Join with free items to see if first order had free pattern
    first_order_items = orders_df.merge(all_items_with_flag, on='order_id')
    first_order_items = first_order_items.merge(first_orders, on='customer_id')
    first_order_items = first_order_items[first_order_items['created_at'] == first_order_items['first_order_date']]

    # Customers whose FIRST order included a free pattern (by name, not just price)
    free_acquired_customers = first_order_items[first_order_items['is_free']]['customer_id'].unique()

    # Check which of these free-acquired customers made PAID purchases
    free_acquired_paid_orders = paid_orders_df[paid_orders_df['customer_id'].isin(free_acquired_customers)]
    converted_customers = free_acquired_paid_orders['customer_id'].unique()

    # Direct buyers (first order was paid)
    direct_buyers = rfm[~rfm['customer_id'].isin(free_acquired_customers)]['customer_id'].unique()

    # Calculate metrics
    total_free_acquired = len(free_acquired_customers)
    converted_count = len(converted_customers)
    conversion_rate = (converted_count / total_free_acquired * 100) if total_free_acquired > 0 else 0

    # Revenue from converted free-acquired customers
    converted_revenue = free_acquired_paid_orders.groupby('customer_id')['total_price'].sum()
    avg_ltv_free_acquired = converted_revenue.mean() if len(converted_revenue) > 0 else 0
    total_revenue_free_acquired = converted_revenue.sum() if len(converted_revenue) > 0 else 0

    # Revenue from direct buyers
    direct_buyer_revenue = paid_orders_df[paid_orders_df['customer_id'].isin(direct_buyers)].groupby('customer_id')['total_price'].sum()
    avg_ltv_direct = direct_buyer_revenue.mean() if len(direct_buyer_revenue) > 0 else 0

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Free Acquired Customers", f"{total_free_acquired:,}")
    with col2:
        st.metric("Converted to Paid", f"{converted_count:,}", delta=f"{conversion_rate:.1f}%")
    with col3:
        st.metric("Avg LTV (Free→Paid)", f"${avg_ltv_free_acquired:.2f}")
    with col4:
        st.metric("Avg LTV (Direct Buyers)", f"${avg_ltv_direct:.2f}")

    st.markdown("---")

    # Funnel visualization - side by side comparison
    st.markdown("### 📊 Acquisition Funnel Comparison")

    col1, col2 = st.columns(2)

    # FREE-TO-PAID FUNNEL
    with col1:
        st.markdown("#### 🎁 Free Pattern Path")

        # Calculate free-to-paid stages
        free_repeat_buyers = len(free_acquired_paid_orders[free_acquired_paid_orders.groupby('customer_id')['order_id'].transform('count') > 1]['customer_id'].unique()) if len(free_acquired_paid_orders) > 0 else 0

        free_funnel_data = pd.DataFrame({
            'Stage': ['Got Free Pattern', 'Made 1st Paid Purchase', 'Became Repeat Buyer'],
            'Customers': [
                total_free_acquired,
                converted_count,
                free_repeat_buyers
            ],
            'Percentage': [
                100,
                (converted_count / total_free_acquired * 100) if total_free_acquired > 0 else 0,
                (free_repeat_buyers / total_free_acquired * 100) if total_free_acquired > 0 else 0
            ]
        })

        fig_free_funnel = px.funnel(
            free_funnel_data,
            x='Customers',
            y='Stage',
            title='Free → Paid Journey',
            color_discrete_sequence=['#84a98c'],
            hover_data={'Percentage': ':.1f'}
        )
        fig_free_funnel.update_layout(height=400)
        st.plotly_chart(fig_free_funnel, use_container_width=True)

        # Stats for free path
        st.markdown(f"""
        **Key Metrics:**
        - **Starting pool:** {total_free_acquired:,} customers
        - **Conversion rate:** {(converted_count / total_free_acquired * 100) if total_free_acquired > 0 else 0:.1f}%
        - **Repeat buyer rate:** {(free_repeat_buyers / converted_count * 100) if converted_count > 0 else 0:.1f}%
        """)

    # DIRECT BUYER FUNNEL
    with col2:
        st.markdown("#### 💰 Direct Purchase Path")

        # Calculate direct buyer stages
        direct_buyer_orders = paid_orders_df[paid_orders_df['customer_id'].isin(direct_buyers)]
        direct_repeat_buyers = len(direct_buyer_orders[direct_buyer_orders.groupby('customer_id')['order_id'].transform('count') > 1]['customer_id'].unique()) if len(direct_buyers) > 0 else 0
        direct_3plus_buyers = len(direct_buyer_orders[direct_buyer_orders.groupby('customer_id')['order_id'].transform('count') >= 3]['customer_id'].unique()) if len(direct_buyers) > 0 else 0

        direct_funnel_data = pd.DataFrame({
            'Stage': ['Made 1st Paid Purchase', 'Became Repeat Buyer', 'Bought 3+ Times'],
            'Customers': [
                len(direct_buyers),
                direct_repeat_buyers,
                direct_3plus_buyers
            ],
            'Percentage': [
                100,
                (direct_repeat_buyers / len(direct_buyers) * 100) if len(direct_buyers) > 0 else 0,
                (direct_3plus_buyers / len(direct_buyers) * 100) if len(direct_buyers) > 0 else 0
            ]
        })

        fig_direct_funnel = px.funnel(
            direct_funnel_data,
            x='Customers',
            y='Stage',
            title='Direct Purchase Journey',
            color_discrete_sequence=['#588157'],
            hover_data={'Percentage': ':.1f'}
        )
        fig_direct_funnel.update_layout(height=400)
        st.plotly_chart(fig_direct_funnel, use_container_width=True)

        # Stats for direct path
        st.markdown(f"""
        **Key Metrics:**
        - **Starting pool:** {len(direct_buyers):,} customers
        - **Repeat buyer rate:** {(direct_repeat_buyers / len(direct_buyers) * 100) if len(direct_buyers) > 0 else 0:.1f}%
        - **3+ purchase rate:** {(direct_3plus_buyers / len(direct_buyers) * 100) if len(direct_buyers) > 0 else 0:.1f}%
        """)

    # Summary comparison
    st.markdown("---")
    st.markdown("### 🔍 Which Path is Better?")

    comparison_metrics = pd.DataFrame({
        'Metric': [
            'Starting Pool',
            'Conversion to 1st Paid',
            'Repeat Buyer Rate',
            'Avg Lifetime Value',
            'Avg Orders per Customer'
        ],
        'Free Pattern Path': [
            f"{total_free_acquired:,}",
            f"{(converted_count / total_free_acquired * 100) if total_free_acquired > 0 else 0:.1f}%",
            f"{(free_repeat_buyers / converted_count * 100) if converted_count > 0 else 0:.1f}%",
            f"${avg_ltv_free_acquired:.2f}",
            f"{free_acquired_paid_orders.groupby('customer_id').size().mean():.1f}" if len(free_acquired_paid_orders) > 0 else "0.0"
        ],
        'Direct Purchase Path': [
            f"{len(direct_buyers):,}",
            "100% (no conversion needed)",
            f"{(direct_repeat_buyers / len(direct_buyers) * 100) if len(direct_buyers) > 0 else 0:.1f}%",
            f"${avg_ltv_direct:.2f}",
            f"{direct_buyer_orders.groupby('customer_id').size().mean():.1f}" if len(direct_buyers) > 0 else "0.0"
        ]
    })

    st.dataframe(comparison_metrics, use_container_width=True, hide_index=True)

    # Winner determination
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🏆 Which Strategy Wins?")

        if avg_ltv_free_acquired > avg_ltv_direct:
            st.success("**Free Pattern Strategy**")
            st.markdown(f"Free→Paid customers have {((avg_ltv_free_acquired / avg_ltv_direct - 1) * 100):.1f}% higher LTV!")
            st.markdown("✅ Keep investing in free pattern promotions")
        else:
            st.info("**Direct Purchase Strategy**")
            st.markdown(f"Direct buyers have {((avg_ltv_direct / avg_ltv_free_acquired - 1) * 100):.1f}% higher LTV")
            st.markdown("💡 Consider if free pattern acquisition cost is worth it")

    with col2:
        st.markdown("#### 💰 CAC Economics")

        # Calculate allowable CAC
        st.markdown(f"""
        **LTV Analysis:**
        - Free→Paid LTV: ${avg_ltv_free_acquired:.2f}
        - Direct Buyer LTV: ${avg_ltv_direct:.2f}
        - Conversion Rate: {conversion_rate:.1f}%

        **Expected Value per Free Signup:**
        """)

        expected_value = avg_ltv_free_acquired * (conversion_rate / 100)
        st.metric("Expected Value", f"${expected_value:.2f}")

        st.markdown(f"""
        **Max Allowable CAC** (at 30% margin):
        """)
        max_cac_30 = expected_value * 0.30
        st.metric("30% Margin", f"${max_cac_30:.2f}")

        max_cac_50 = expected_value * 0.50
        st.metric("50% Margin", f"${max_cac_50:.2f}")

    st.markdown("---")

    # Time to conversion
    st.markdown("#### ⏱️ Time to First Paid Purchase")

    # Calculate days from first free to first paid
    conversion_times = []
    for customer_id in converted_customers:
        first_free_order = orders_df[
            (orders_df['customer_id'] == customer_id) &
            (orders_df['order_id'].isin(free_items['order_id']))
        ]['created_at'].min()

        first_paid_order = paid_orders_df[paid_orders_df['customer_id'] == customer_id]['created_at'].min()

        if pd.notna(first_free_order) and pd.notna(first_paid_order) and first_paid_order > first_free_order:
            days_to_convert = (first_paid_order - first_free_order).days
            conversion_times.append(days_to_convert)

    if conversion_times:
        conversion_times_df = pd.DataFrame({'days': conversion_times})

        col1, col2 = st.columns(2)

        with col1:
            avg_days = sum(conversion_times) / len(conversion_times)
            median_days = sorted(conversion_times)[len(conversion_times)//2]

            st.metric("Avg Days to Convert", f"{avg_days:.0f}")
            st.metric("Median Days to Convert", f"{median_days:.0f}")

            # Cohort breakdown
            st.markdown("**Conversion Timeline:**")
            st.markdown(f"- Within 7 days: {len([d for d in conversion_times if d <= 7])}")
            st.markdown(f"- Within 30 days: {len([d for d in conversion_times if d <= 30])}")
            st.markdown(f"- Within 90 days: {len([d for d in conversion_times if d <= 90])}")
            st.markdown(f"- Within 365 days: {len([d for d in conversion_times if d <= 365])}")

        with col2:
            fig_conversion_time = px.histogram(
                conversion_times_df,
                x='days',
                nbins=30,
                title='Distribution of Days to First Paid Purchase',
                labels={'days': 'Days', 'count': 'Number of Customers'},
                color_discrete_sequence=['#84a98c']
            )
            st.plotly_chart(fig_conversion_time, use_container_width=True)

    st.markdown("---")

    # Comparative analysis
    st.markdown("#### 📈 Free-Acquired vs Direct Buyers")

    comparison_data = pd.DataFrame({
        'Metric': ['Avg LTV', 'Avg Orders', 'Avg Order Value'],
        'Free→Paid': [
            avg_ltv_free_acquired,
            free_acquired_paid_orders.groupby('customer_id').size().mean() if len(free_acquired_paid_orders) > 0 else 0,
            free_acquired_paid_orders['total_price'].mean() if len(free_acquired_paid_orders) > 0 else 0
        ],
        'Direct Buyers': [
            avg_ltv_direct,
            paid_orders_df[paid_orders_df['customer_id'].isin(direct_buyers)].groupby('customer_id').size().mean() if len(direct_buyers) > 0 else 0,
            paid_orders_df[paid_orders_df['customer_id'].isin(direct_buyers)]['total_price'].mean() if len(direct_buyers) > 0 else 0
        ]
    })

    fig_comparison = px.bar(
        comparison_data,
        x='Metric',
        y=['Free→Paid', 'Direct Buyers'],
        title='Customer Value Comparison',
        barmode='group',
        color_discrete_sequence=['#84a98c', '#588157']
    )
    st.plotly_chart(fig_comparison, use_container_width=True)

    st.info("""
    **💡 Insights for Acquisition Strategy:**
    - If Free→Paid LTV > Direct Buyer LTV: Free patterns are attracting higher-value customers
    - Use Max CAC to determine ad spend limits for free pattern promotions
    - Focus remarketing on customers within the median conversion window
    - Consider email nurture sequences based on average days to convert
    """)

    st.markdown("---")

    # Pattern preferences by segment
    st.markdown("### 🛍️ Pattern Preferences by Segment")

    selected_segment = st.selectbox("Select a segment to analyze:", rfm['segment'].unique())

    segment_customers = rfm[rfm['segment'] == selected_segment]['customer_id']
    segment_orders = paid_orders_df[paid_orders_df['customer_id'].isin(segment_customers)]
    segment_items = paid_items[paid_items['order_id'].isin(segment_orders['order_id'])]

    if len(segment_items) > 0:
        top_patterns = segment_items.groupby('product_title').agg({
            'quantity': 'sum',
            'revenue': 'sum',
            'order_id': 'nunique'
        }).sort_values('quantity', ascending=False).head(15).reset_index()

        top_patterns.columns = ['Pattern', 'Units Sold', 'Revenue', 'Orders']

        col1, col2 = st.columns([2, 1])

        with col1:
            fig_bar = px.bar(
                top_patterns,
                x='Units Sold',
                y='Pattern',
                orientation='h',
                title=f'Top Patterns for {selected_segment}',
                color='Revenue',
                color_continuous_scale='Teal'
            )
            fig_bar.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_bar, use_container_width=True)

        with col2:
            st.markdown(f"#### {selected_segment} Insights")
            st.markdown(f"**Customers:** {len(segment_customers):,}")
            st.markdown(f"**Total Orders:** {len(segment_orders):,}")
            st.markdown(f"**Revenue:** ${segment_items['revenue'].sum():,.0f}")
            st.markdown(f"**Avg Order Value:** ${segment_orders['total_price'].mean():.2f}")

            st.markdown("---")
            st.markdown("**Top 5 Patterns:**")
            for idx, row in top_patterns.head(5).iterrows():
                st.markdown(f"**{row['Pattern'][:40]}**")
                st.markdown(f"   {int(row['Units Sold'])} units • ${row['Revenue']:,.0f}")
    else:
        st.info(f"No purchase data available for {selected_segment}")

    st.markdown("---")

    # Cohort analysis
    st.markdown("### 📅 Cohort Analysis")

    cohort_selector = st.radio(
        "View by:",
        ["Customer Lifetime", "Repeat Purchase Rate"],
        horizontal=True
    )

    if cohort_selector == "Customer Lifetime":
        # Lifetime value distribution
        rfm_display = rfm.sort_values('monetary_value', ascending=False).head(100)

        fig_lifetime = px.bar(
            rfm_display,
            x=rfm_display.index,
            y='monetary_value',
            color='segment',
            title='Top 100 Customers by Lifetime Value',
            labels={'monetary_value': 'Total Spent ($)', 'index': 'Customer Rank'}
        )
        fig_lifetime.update_layout(height=400, showlegend=True)
        st.plotly_chart(fig_lifetime, use_container_width=True)

    else:
        # Repeat purchase rate
        repeat_customers = rfm[rfm['frequency'] > 1]['customer_id'].nunique()
        total_customers = len(rfm)
        repeat_rate = repeat_customers / total_customers * 100

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Repeat Customers", f"{repeat_customers:,}")
        with col2:
            st.metric("Repeat Purchase Rate", f"{repeat_rate:.1f}%")
        with col3:
            multi_buyers = rfm[rfm['frequency'] >= 3]['customer_id'].nunique()
            st.metric("3+ Purchases", f"{multi_buyers:,}", delta=f"{multi_buyers/total_customers*100:.1f}%")

        # Distribution by number of orders
        freq_dist = rfm['frequency'].value_counts().sort_index().head(20).reset_index()
        freq_dist.columns = ['Number of Orders', 'Customers']

        fig_repeat = px.bar(
            freq_dist,
            x='Number of Orders',
            y='Customers',
            title='Customer Distribution by Order Count',
            color='Customers',
            color_continuous_scale='Greens'
        )
        st.plotly_chart(fig_repeat, use_container_width=True)

def show_geographic_insights(orders_df, line_items_df):
    """Geographic analysis"""
    st.markdown('<p class="main-header">🌍 Geographic Insights</p>', unsafe_allow_html=True)
    st.markdown("### Global Sales Distribution & Regional Performance")

    # Merge data
    merged_df = orders_df.merge(line_items_df, on='order_id')

    # Time filter
    col1, col2 = st.columns(2)
    with col1:
        time_filter = st.selectbox("Time Period", [30, 60, 90, 180, 365, "All Time"], index=4)

    if time_filter != "All Time":
        cutoff = pd.Timestamp.now(tz='UTC') - timedelta(days=time_filter)
        filtered_df = merged_df[merged_df['created_at'] >= cutoff]
        filtered_orders = orders_df[orders_df['created_at'] >= cutoff]
    else:
        filtered_df = merged_df
        filtered_orders = orders_df

    # Country-level aggregations
    country_stats = filtered_orders.groupby('country').agg({
        'order_id': 'count',
        'total_price': 'sum',
        'customer_id': 'nunique'
    }).reset_index()
    country_stats.columns = ['country', 'orders', 'revenue', 'customers']
    country_stats['avg_order_value'] = country_stats['revenue'] / country_stats['orders']

    # Sort by revenue
    country_stats = country_stats.sort_values('revenue', ascending=False)

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Countries", len(country_stats))
    with col2:
        top_country = country_stats.iloc[0]
        st.metric("Top Market", top_country['country'])
    with col3:
        top_revenue_pct = top_country['revenue'] / country_stats['revenue'].sum() * 100
        st.metric("Top Market Share", f"{top_revenue_pct:.1f}%")
    with col4:
        international_orders = len(country_stats) - 1
        st.metric("International Markets", international_orders)

    st.markdown("---")

    # World map
    st.markdown("### 🗺️ Global Revenue Heatmap")

    fig_map = px.choropleth(
        country_stats,
        locations='country',
        locationmode='country names',
        color='revenue',
        hover_name='country',
        hover_data={
            'revenue': ':$,.0f',
            'orders': ':,',
            'customers': ':,',
            'avg_order_value': ':$.2f'
        },
        color_continuous_scale='Teal',
        title='Revenue by Country'
    )
    fig_map.update_layout(height=500)
    st.plotly_chart(fig_map, use_container_width=True)

    st.markdown("---")

    # Top countries comparison
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 📊 Top 20 Countries by Revenue")
        top_20 = country_stats.head(20)

        fig_bar = px.bar(
            top_20,
            x='revenue',
            y='country',
            orientation='h',
            color='orders',
            hover_data=['customers', 'avg_order_value'],
            title='Revenue Distribution',
            labels={'revenue': 'Revenue ($)', 'country': 'Country', 'orders': 'Orders'},
            color_continuous_scale='Greens'
        )
        fig_bar.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.markdown("### 🥧 Revenue Concentration")
        top_5 = country_stats.head(5).copy()
        others_revenue = country_stats.iloc[5:]['revenue'].sum()
        top_5 = pd.concat([
            top_5,
            pd.DataFrame([{
                'country': f'Others ({len(country_stats)-5})',
                'revenue': others_revenue,
                'orders': 0,
                'customers': 0
            }])
        ])

        fig_pie = px.pie(
            top_5,
            values='revenue',
            names='country',
            title='Revenue Share',
            color_discrete_sequence=px.colors.sequential.Teal
        )
        st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("### 💰 Top 5 Markets")
        for idx, row in country_stats.head(5).iterrows():
            st.markdown(f"**{row['country']}**")
            st.markdown(f"   ${row['revenue']:,.0f} • {int(row['orders'])} orders")

    st.markdown("---")

    # Country performance table
    st.markdown("### 📋 Country Performance Details")

    display_countries = country_stats.copy()
    display_countries.columns = ['Country', 'Orders', 'Revenue', 'Customers', 'Avg Order Value']
    display_countries['Revenue'] = display_countries['Revenue'].round(0).astype(int)
    display_countries['Avg Order Value'] = display_countries['Avg Order Value'].round(2)

    st.dataframe(display_countries, use_container_width=True, height=400)

    st.markdown("---")

    # Country-specific pattern analysis
    st.markdown("### 🔍 Country-Specific Pattern Preferences")

    top_10_countries = country_stats.head(10)['country'].tolist()
    selected_country = st.selectbox("Select a country to analyze:", top_10_countries)

    if selected_country:
        country_orders = filtered_orders[filtered_orders['country'] == selected_country]
        country_items = filtered_df[filtered_df['order_id'].isin(country_orders['order_id'])]

        if len(country_items) > 0:
            top_patterns = country_items.groupby('product_title').agg({
                'quantity': 'sum',
                'revenue': 'sum'
            }).sort_values('quantity', ascending=False).head(15).reset_index()

            top_patterns.columns = ['Pattern', 'Units', 'Revenue']

            col1, col2 = st.columns([2, 1])

            with col1:
                fig_country = px.bar(
                    top_patterns,
                    x='Units',
                    y='Pattern',
                    orientation='h',
                    color='Revenue',
                    title=f'Top Patterns in {selected_country}',
                    color_continuous_scale='Teal'
                )
                fig_country.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig_country, use_container_width=True)

            with col2:
                st.markdown(f"#### {selected_country} Stats")
                st.markdown(f"**Orders:** {len(country_orders):,}")
                st.markdown(f"**Revenue:** ${country_orders['total_price'].sum():,.0f}")
                st.markdown(f"**Customers:** {country_orders['customer_id'].nunique():,}")
                st.markdown(f"**Avg Order:** ${country_orders['total_price'].mean():.2f}")

                st.markdown("---")
                st.markdown("**Top 5 Patterns:**")
                for idx, row in top_patterns.head(5).iterrows():
                    st.markdown(f"**{row['Pattern'][:35]}**")
                    st.markdown(f"   {int(row['Units'])} units")

    st.markdown("---")

    # Regional groupings
    st.markdown("### 🌐 Regional Analysis")

    # Simple region mapping
    region_map = {
        'United States': 'North America',
        'Canada': 'North America',
        'Mexico': 'North America',
        'United Kingdom': 'Europe',
        'Germany': 'Europe',
        'France': 'Europe',
        'Italy': 'Europe',
        'Spain': 'Europe',
        'Netherlands': 'Europe',
        'Belgium': 'Europe',
        'Switzerland': 'Europe',
        'Austria': 'Europe',
        'Sweden': 'Europe',
        'Norway': 'Europe',
        'Denmark': 'Europe',
        'Finland': 'Europe',
        'Ireland': 'Europe',
        'Poland': 'Europe',
        'Australia': 'Oceania',
        'New Zealand': 'Oceania',
        'Japan': 'Asia',
        'South Korea': 'Asia',
        'Singapore': 'Asia',
        'Hong Kong': 'Asia',
        'India': 'Asia',
        'China': 'Asia'
    }

    country_stats['region'] = country_stats['country'].map(region_map).fillna('Other')

    region_stats = country_stats.groupby('region').agg({
        'orders': 'sum',
        'revenue': 'sum',
        'customers': 'sum'
    }).reset_index().sort_values('revenue', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        fig_region = px.bar(
            region_stats,
            x='region',
            y='revenue',
            color='orders',
            title='Revenue by Region',
            labels={'revenue': 'Revenue ($)', 'region': 'Region', 'orders': 'Orders'},
            color_continuous_scale='Teal'
        )
        st.plotly_chart(fig_region, use_container_width=True)

    with col2:
        fig_region_pie = px.pie(
            region_stats,
            values='revenue',
            names='region',
            title='Regional Revenue Share',
            color_discrete_sequence=px.colors.sequential.Teal
        )
        st.plotly_chart(fig_region_pie, use_container_width=True)

def show_campaign_performance(orders_df, line_items_df):
    """Campaign analytics"""
    st.markdown('<p class="main-header">📢 Campaign Performance</p>', unsafe_allow_html=True)
    st.markdown("### Marketing Attribution & Campaign ROI")

    # Time filter
    col1, col2 = st.columns(2)
    with col1:
        time_filter = st.selectbox("Time Period", [30, 60, 90, 180, 365, "All Time"], index=2)

    if time_filter != "All Time":
        cutoff = pd.Timestamp.now(tz='UTC') - timedelta(days=time_filter)
        filtered_orders = orders_df[orders_df['created_at'] >= cutoff]
    else:
        filtered_orders = orders_df

    # Filter out orders without UTM data
    tracked_orders = filtered_orders[
        (filtered_orders['utm_source'].notna()) |
        (filtered_orders['utm_medium'].notna()) |
        (filtered_orders['utm_campaign'].notna())
    ]

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        tracked_pct = len(tracked_orders) / len(filtered_orders) * 100 if len(filtered_orders) > 0 else 0
        st.metric("Tracked Orders", f"{len(tracked_orders):,}", delta=f"{tracked_pct:.1f}% of total")
    with col2:
        tracked_revenue = tracked_orders['total_price'].sum()
        st.metric("Tracked Revenue", f"${tracked_revenue:,.0f}")
    with col3:
        unique_campaigns = tracked_orders['utm_campaign'].nunique()
        st.metric("Active Campaigns", unique_campaigns)
    with col4:
        unique_sources = tracked_orders['utm_source'].nunique()
        st.metric("Traffic Sources", unique_sources)

    st.markdown("---")

    # UTM Source Analysis
    st.markdown("### 📊 Performance by Traffic Source")

    source_stats = tracked_orders.groupby('utm_source').agg({
        'order_id': 'count',
        'total_price': 'sum',
        'customer_id': 'nunique'
    }).reset_index()
    source_stats.columns = ['source', 'orders', 'revenue', 'customers']
    source_stats['avg_order_value'] = source_stats['revenue'] / source_stats['orders']
    source_stats = source_stats.sort_values('revenue', ascending=False)

    col1, col2 = st.columns([2, 1])

    with col1:
        if len(source_stats) > 0:
            fig_source = px.bar(
                source_stats.head(15),
                x='source',
                y='revenue',
                color='orders',
                title='Revenue by Source',
                labels={'revenue': 'Revenue ($)', 'source': 'UTM Source', 'orders': 'Orders'},
                color_continuous_scale='Teal'
            )
            st.plotly_chart(fig_source, use_container_width=True)
        else:
            st.info("No UTM source data available")

    with col2:
        if len(source_stats) > 0:
            fig_source_pie = px.pie(
                source_stats,
                values='revenue',
                names='source',
                title='Revenue Share by Source',
                color_discrete_sequence=px.colors.sequential.Teal
            )
            st.plotly_chart(fig_source_pie, use_container_width=True)

    st.markdown("---")

    # UTM Medium Analysis
    st.markdown("### 🎯 Performance by Medium")

    medium_stats = tracked_orders.groupby('utm_medium').agg({
        'order_id': 'count',
        'total_price': 'sum',
        'customer_id': 'nunique'
    }).reset_index()
    medium_stats.columns = ['medium', 'orders', 'revenue', 'customers']
    medium_stats['avg_order_value'] = medium_stats['revenue'] / medium_stats['orders']
    medium_stats = medium_stats.sort_values('revenue', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        if len(medium_stats) > 0:
            fig_medium = px.bar(
                medium_stats,
                x='medium',
                y='revenue',
                color='avg_order_value',
                title='Revenue by Medium',
                labels={'revenue': 'Revenue ($)', 'medium': 'UTM Medium', 'avg_order_value': 'AOV'},
                color_continuous_scale='Greens'
            )
            st.plotly_chart(fig_medium, use_container_width=True)

    with col2:
        if len(medium_stats) > 0:
            fig_medium_orders = px.bar(
                medium_stats,
                x='medium',
                y='orders',
                color='customers',
                title='Orders by Medium',
                labels={'orders': 'Orders', 'medium': 'UTM Medium', 'customers': 'Customers'},
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig_medium_orders, use_container_width=True)

    st.markdown("---")

    # Campaign Analysis
    st.markdown("### 🚀 Top Campaigns")

    campaign_stats = tracked_orders.groupby('utm_campaign').agg({
        'order_id': 'count',
        'total_price': 'sum',
        'customer_id': 'nunique',
        'created_at': ['min', 'max']
    }).reset_index()
    campaign_stats.columns = ['campaign', 'orders', 'revenue', 'customers', 'first_order', 'last_order']
    campaign_stats['avg_order_value'] = campaign_stats['revenue'] / campaign_stats['orders']
    campaign_stats['duration_days'] = (
        pd.to_datetime(campaign_stats['last_order']) - pd.to_datetime(campaign_stats['first_order'])
    ).dt.days + 1
    campaign_stats = campaign_stats.sort_values('revenue', ascending=False)

    # Top 20 campaigns
    top_campaigns = campaign_stats.head(20)

    fig_campaigns = px.bar(
        top_campaigns,
        x='revenue',
        y='campaign',
        orientation='h',
        color='orders',
        hover_data=['customers', 'avg_order_value', 'duration_days'],
        title='Top 20 Campaigns by Revenue',
        labels={'revenue': 'Revenue ($)', 'campaign': 'Campaign', 'orders': 'Orders'},
        color_continuous_scale='Viridis'
    )
    fig_campaigns.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_campaigns, use_container_width=True)

    st.markdown("---")

    # Campaign details table
    st.markdown("### 📋 Campaign Performance Details")

    display_campaigns = campaign_stats.copy()
    display_campaigns['first_order'] = pd.to_datetime(display_campaigns['first_order']).dt.strftime('%Y-%m-%d')
    display_campaigns['last_order'] = pd.to_datetime(display_campaigns['last_order']).dt.strftime('%Y-%m-%d')
    display_campaigns.columns = ['Campaign', 'Orders', 'Revenue', 'Customers', 'First Order', 'Last Order', 'AOV', 'Duration (days)']
    display_campaigns['Revenue'] = display_campaigns['Revenue'].round(0).astype(int)
    display_campaigns['AOV'] = display_campaigns['AOV'].round(2)

    st.dataframe(display_campaigns, use_container_width=True, height=400)

    st.markdown("---")

    # Channel mix analysis
    st.markdown("### 📈 Channel Performance Over Time")

    # Group by month and source
    tracked_orders['year_month'] = tracked_orders['created_at'].dt.to_period('M').astype(str)

    monthly_source = tracked_orders.groupby(['year_month', 'utm_source']).agg({
        'total_price': 'sum',
        'order_id': 'count'
    }).reset_index()
    monthly_source.columns = ['month', 'source', 'revenue', 'orders']

    # Get top 5 sources
    top_sources = source_stats.head(5)['source'].tolist()
    monthly_source_top = monthly_source[monthly_source['source'].isin(top_sources)]

    if len(monthly_source_top) > 0:
        fig_trend = px.line(
            monthly_source_top,
            x='month',
            y='revenue',
            color='source',
            title='Revenue Trend by Top Sources',
            labels={'revenue': 'Revenue ($)', 'month': 'Month', 'source': 'Source'},
            markers=True
        )
        fig_trend.update_layout(height=400)
        st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("---")

    # Conversion analysis by source
    st.markdown("### 🎪 Source-to-Customer Conversion")

    if len(source_stats) > 0:
        source_stats['conversion_rate'] = (source_stats['customers'] / source_stats['orders'] * 100).round(2)

        col1, col2 = st.columns(2)

        with col1:
            fig_conversion = px.scatter(
                source_stats,
                x='orders',
                y='avg_order_value',
                size='revenue',
                color='conversion_rate',
                hover_data=['source', 'customers'],
                title='Order Value vs Volume by Source',
                labels={
                    'orders': 'Number of Orders',
                    'avg_order_value': 'Average Order Value ($)',
                    'conversion_rate': 'Conversion %'
                },
                color_continuous_scale='Teal'
            )
            st.plotly_chart(fig_conversion, use_container_width=True)

        with col2:
            st.markdown("#### 🏆 Best Performing Sources")
            top_5_sources = source_stats.head(5)
            for idx, row in top_5_sources.iterrows():
                st.markdown(f"**{row['source']}**")
                st.markdown(f"   Revenue: ${row['revenue']:,.0f} | Orders: {int(row['orders'])} | AOV: ${row['avg_order_value']:.2f}")
                st.markdown(f"   Customers: {int(row['customers'])} | Conversion: {row['conversion_rate']:.1f}%")
                st.markdown("---")

    # Campaign effectiveness score
    st.markdown("---")
    st.markdown("### ⭐ Campaign Effectiveness Score")

    if len(campaign_stats) > 0:
        # Normalize metrics for scoring
        campaign_stats['revenue_score'] = (campaign_stats['revenue'] / campaign_stats['revenue'].max() * 40).round(0)
        campaign_stats['order_score'] = (campaign_stats['orders'] / campaign_stats['orders'].max() * 30).round(0)
        campaign_stats['aov_score'] = (campaign_stats['avg_order_value'] / campaign_stats['avg_order_value'].max() * 20).round(0)
        campaign_stats['customer_score'] = (campaign_stats['customers'] / campaign_stats['customers'].max() * 10).round(0)

        campaign_stats['effectiveness_score'] = (
            campaign_stats['revenue_score'] +
            campaign_stats['order_score'] +
            campaign_stats['aov_score'] +
            campaign_stats['customer_score']
        )

        top_effective = campaign_stats.nlargest(15, 'effectiveness_score')[
            ['campaign', 'effectiveness_score', 'revenue', 'orders', 'avg_order_value']
        ]

        fig_effectiveness = px.bar(
            top_effective,
            x='effectiveness_score',
            y='campaign',
            orientation='h',
            color='revenue',
            title='Most Effective Campaigns (Composite Score)',
            labels={'effectiveness_score': 'Effectiveness Score (0-100)', 'campaign': 'Campaign'},
            color_continuous_scale='Teal'
        )
        fig_effectiveness.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_effectiveness, use_container_width=True)

        st.markdown("""
        **Scoring Breakdown:**
        - Revenue: 40 points
        - Orders: 30 points
        - Average Order Value: 20 points
        - Unique Customers: 10 points
        """)

def show_weekly_specials_ai(orders_df, line_items_df):
    """AI-powered weekly specials optimizer"""
    st.markdown('<p class="main-header">✨ Weekly Specials AI</p>', unsafe_allow_html=True)
    st.markdown("### Smart Pattern Selection with Predictive Scoring")

    # Load recent specials to avoid repetition
    import json
    specials_file = Path(__file__).parent.parent / 'Docs' / 'weeklySpecials.json'
    recently_featured = set()
    if specials_file.exists():
        with open(specials_file, 'r') as f:
            data = json.load(f)
            for entry in data.get('weekly_specials_history', []):
                recently_featured.update(entry.get('patterns', []))

    # Load free patterns config to exclude
    free_patterns_file = Path(__file__).parent.parent / 'Docs' / 'free_patterns_config.json'
    free_pattern_names = set()
    if free_patterns_file.exists():
        with open(free_patterns_file, 'r') as f:
            free_config = json.load(f)
            for pattern in free_config.get('free_patterns', []):
                free_pattern_names.add(pattern['name'])

    st.markdown(f"📋 Excluding {len(recently_featured)} recently featured patterns + {len(free_pattern_names)} free patterns (Harper, Valley, Mojo, etc.)")

    # Settings
    col1, col2 = st.columns(2)
    with col1:
        analysis_days = st.selectbox("Analysis Period", [30, 60, 90, 180], index=2)
    with col2:
        num_suggestions = st.slider("Number of pattern sets to suggest", 2, 5, 3)

    st.markdown("---")

    # Merge data
    merged_df = orders_df.merge(line_items_df, on='order_id')

    # Calculate all pattern metrics
    cutoff = pd.Timestamp.now(tz='UTC') - timedelta(days=analysis_days)
    recent_df = merged_df[merged_df['created_at'] >= cutoff]

    # All-time stats
    all_time_stats = merged_df.groupby('product_title').agg({
        'quantity': 'sum',
        'revenue': 'sum',
        'created_at': ['min', 'max']
    }).reset_index()
    all_time_stats.columns = ['product_title', 'total_units', 'total_revenue', 'first_sale', 'last_sale']

    # Recent stats
    recent_stats = recent_df.groupby('product_title').agg({
        'quantity': 'sum',
        'revenue': 'sum'
    }).reset_index()
    recent_stats.columns = ['product_title', 'recent_units', 'recent_revenue']

    # Merge
    pattern_metrics = all_time_stats.merge(recent_stats, on='product_title', how='left')
    pattern_metrics['recent_units'] = pattern_metrics['recent_units'].fillna(0)
    pattern_metrics['recent_revenue'] = pattern_metrics['recent_revenue'].fillna(0)

    # Calculate age
    now = pd.Timestamp.now(tz='UTC')
    pattern_metrics['age_days'] = (now - pd.to_datetime(pattern_metrics['first_sale'])).dt.days
    pattern_metrics['days_since_launch'] = pattern_metrics['age_days']

    # Calculate momentum
    merged_df['year_month'] = merged_df['created_at'].dt.to_period('M')
    monthly_stats = merged_df.groupby(['product_title', 'year_month']).agg({
        'quantity': 'sum'
    }).reset_index()

    def calc_momentum(product_title):
        product_monthly = monthly_stats[monthly_stats['product_title'] == product_title].sort_values('year_month')
        if len(product_monthly) < 2:
            return 0
        recent_months = product_monthly.tail(3)['quantity'].values
        if len(recent_months) < 2:
            return 0
        recent = recent_months[-1]
        previous_avg = recent_months[:-1].mean()
        if previous_avg == 0:
            return 100 if recent > 0 else 0
        return ((recent - previous_avg) / previous_avg) * 100

    pattern_metrics['momentum_pct'] = pattern_metrics['product_title'].apply(calc_momentum)

    # Filter out recently featured, free patterns, and low performers
    def is_free_pattern(title):
        """Check if pattern title contains any free pattern name"""
        title_lower = title.lower()
        for free_name in free_pattern_names:
            if free_name.lower() in title_lower:
                return True
        return False

    pattern_metrics['is_free'] = pattern_metrics['product_title'].apply(is_free_pattern)

    pattern_metrics = pattern_metrics[
        (~pattern_metrics['product_title'].isin(recently_featured)) &
        (~pattern_metrics['is_free']) &
        (pattern_metrics['total_units'] >= 10) &
        (pattern_metrics['recent_units'] > 0)  # Must have recent sales in the analysis period
    ]

    # SCORING ALGORITHM
    # 1. Momentum Score (0-30 points)
    def score_momentum(momentum):
        if momentum >= 100:
            return 30
        elif momentum >= 50:
            return 25
        elif momentum >= 20:
            return 20
        elif momentum >= 0:
            return 15
        elif momentum >= -20:
            return 10
        else:
            return 5

    pattern_metrics['momentum_score'] = pattern_metrics['momentum_pct'].apply(score_momentum)

    # 2. Historical Performance (0-25 points) - based on all-time sales
    max_units = pattern_metrics['total_units'].max()
    pattern_metrics['historical_score'] = (pattern_metrics['total_units'] / max_units * 25).round(0)

    # 3. Revenue/Margin Score (0-20 points) - revenue per unit
    pattern_metrics['revenue_per_unit'] = pattern_metrics['total_revenue'] / pattern_metrics['total_units']
    max_rpu = pattern_metrics['revenue_per_unit'].max()
    pattern_metrics['margin_score'] = (pattern_metrics['revenue_per_unit'] / max_rpu * 20).round(0)

    # 4. Freshness Bonus (0-10 points) - never featured before
    pattern_metrics['freshness_score'] = 10  # All are fresh since we filtered recent ones

    # 5. Complementarity will be calculated for sets
    # Total preliminary score (without complementarity)
    pattern_metrics['base_score'] = (
        pattern_metrics['momentum_score'] +
        pattern_metrics['historical_score'] +
        pattern_metrics['margin_score'] +
        pattern_metrics['freshness_score']
    )

    # Sort by base score
    top_patterns = pattern_metrics.sort_values('base_score', ascending=False).head(30)

    # Calculate market basket data for complementarity
    multi_order_items = line_items_df.groupby('order_id').filter(lambda x: len(x) > 1)
    product_pairs = {}

    for order_id in multi_order_items['order_id'].unique():
        products = multi_order_items[multi_order_items['order_id'] == order_id]['product_title'].unique()
        for i, prod_a in enumerate(products):
            for prod_b in products[i+1:]:
                pair_key = tuple(sorted([prod_a, prod_b]))
                product_pairs[pair_key] = product_pairs.get(pair_key, 0) + 1

    def get_complementarity_score(pattern_a, pattern_b):
        """Calculate how often two patterns are bought together"""
        pair_key = tuple(sorted([pattern_a, pattern_b]))
        times_together = product_pairs.get(pair_key, 0)
        if times_together >= 20:
            return 15
        elif times_together >= 10:
            return 12
        elif times_together >= 5:
            return 8
        elif times_together >= 2:
            return 5
        else:
            return 0

    # Generate pattern sets
    suggested_sets = []

    # Set 1: Top scorer + complementary patterns
    if len(top_patterns) >= 3:
        anchor = top_patterns.iloc[0]
        companions = []

        for idx, pattern in top_patterns.iloc[1:10].iterrows():
            comp_score = get_complementarity_score(anchor['product_title'], pattern['product_title'])
            total_score = pattern['base_score'] + comp_score
            companions.append({
                'pattern': pattern['product_title'],
                'base_score': pattern['base_score'],
                'comp_score': comp_score,
                'total_score': total_score,
                'metrics': pattern
            })

        companions = sorted(companions, key=lambda x: x['total_score'], reverse=True)[:2]

        set1_patterns = [anchor] + [c['metrics'] for c in companions[:2]]
        set1_comp = sum([c['comp_score'] for c in companions[:2]]) / 2

        suggested_sets.append({
            'name': f"Top Performer Bundle (Score: {int(anchor['base_score'] + set1_comp)}/100)",
            'patterns': set1_patterns,
            'avg_comp': set1_comp,
            'reasoning': f"Built around highest-scoring pattern with strong complementary picks"
        })

    # Set 2: High momentum patterns
    if len(top_patterns) >= 6:
        high_momentum = top_patterns.nlargest(10, 'momentum_pct')
        if len(high_momentum) >= 3:
            set2_patterns = high_momentum.head(3)
            avg_score = set2_patterns['base_score'].mean()

            suggested_sets.append({
                'name': f"Rising Stars Bundle (Score: {int(avg_score)}/100)",
                'patterns': set2_patterns.to_dict('records'),
                'avg_comp': 0,
                'reasoning': f"Fastest-growing patterns with strong momentum"
            })

    # Set 3: Revenue optimizers
    if len(top_patterns) >= 9:
        high_revenue = top_patterns.nlargest(10, 'revenue_per_unit')
        if len(high_revenue) >= 3:
            set3_patterns = high_revenue.head(3)
            avg_score = set3_patterns['base_score'].mean()

            suggested_sets.append({
                'name': f"Premium Revenue Bundle (Score: {int(avg_score)}/100)",
                'patterns': set3_patterns.to_dict('records'),
                'avg_comp': 0,
                'reasoning': f"Highest revenue-per-unit patterns for maximum earnings"
            })

    # Display suggested sets
    st.markdown("### 🎯 AI-Recommended Pattern Sets")

    for i, pattern_set in enumerate(suggested_sets[:num_suggestions], 1):
        with st.expander(f"**Set #{i}: {pattern_set['name']}**", expanded=(i==1)):
            st.markdown(f"**Strategy:** {pattern_set['reasoning']}")

            if pattern_set['avg_comp'] > 0:
                st.markdown(f"**Bundle Synergy:** {pattern_set['avg_comp']:.1f}/15 (complementarity score)")

            st.markdown("---")

            for j, pattern in enumerate(pattern_set['patterns'], 1):
                # All patterns are now either pandas Series (from Set 1) or dicts (from Set 2/3)
                if isinstance(pattern, dict):
                    title = pattern['product_title']
                    momentum = pattern.get('momentum_pct', 0)
                    units = pattern.get('recent_units', 0)
                    total_units = pattern.get('total_units', 0)
                    revenue = pattern.get('recent_revenue', 0)
                    score = pattern.get('base_score', 0)
                    age = pattern.get('age_days', 0)
                else:  # pandas Series
                    title = pattern['product_title']
                    momentum = pattern.get('momentum_pct', 0)
                    units = pattern.get('recent_units', 0)
                    total_units = pattern.get('total_units', 0)
                    revenue = pattern.get('recent_revenue', 0)
                    score = pattern.get('base_score', 0)
                    age = pattern.get('age_days', 0)

                st.markdown(f"### {j}. {title}")

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Score", f"{int(score)}/85")
                with col2:
                    st.metric("Momentum", f"{momentum:+.1f}%")
                with col3:
                    st.metric(f"Recent ({analysis_days}d)", f"{int(units)} units")
                with col4:
                    st.metric("All-time", f"{int(total_units)} units")

                st.markdown(f"**Revenue (recent):** ${revenue:,.0f} | **Age:** {int(age)} days")
                st.markdown("---")

            # Predicted revenue
            total_recent = sum([
                p.get('recent_revenue', 0) if isinstance(p, dict) else p['recent_revenue']
                for p in pattern_set['patterns']
            ])
            estimated_min = total_recent * 0.8
            estimated_max = total_recent * 1.3

            st.markdown(f"### 💰 Predicted Revenue")
            st.markdown(f"Based on recent {analysis_days}-day performance:")
            st.markdown(f"**${estimated_min:,.0f} - ${estimated_max:,.0f}** for the promotional period")

    st.markdown("---")

    # Export functionality
    st.markdown("### 📤 Export Newsletter Metadata")

    if st.button("Generate Newsletter Metadata for Top Set"):
        if suggested_sets:
            top_set = suggested_sets[0]
            pattern_titles = [
                p['product_title'] if isinstance(p, dict) else p['product_title']
                for p in top_set['patterns']
            ]

            metadata = {
                'campaign_date': pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d'),
                'patterns': pattern_titles,
                'set_name': top_set['name'],
                'reasoning': top_set['reasoning'],
                'predicted_revenue_range': f"${total_recent*0.8:,.0f} - ${total_recent*1.3:,.0f}"
            }

            st.json(metadata)
            st.success("✓ Metadata generated! Copy this to your newsletter workflow.")
        else:
            st.warning("No suggested sets available")

    # Full scoring table
    st.markdown("---")
    st.markdown("### 📊 All Pattern Scores")

    display_scores = top_patterns[[
        'product_title', 'base_score', 'momentum_score', 'historical_score',
        'margin_score', 'freshness_score', 'recent_units', 'momentum_pct'
    ]].copy()

    display_scores.columns = [
        'Pattern', 'Total Score', 'Momentum', 'Historical',
        'Margin', 'Freshness', 'Recent Units', 'Momentum %'
    ]

    st.dataframe(display_scores, use_container_width=True, height=400)

if __name__ == "__main__":
    main()
