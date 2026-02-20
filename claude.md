
This is a helper to run everyday business tasks for SInclair Patterns
Always check what is the current year using now functions, especially for static templates

When commit - do not leave Co Authoring note
Ask before doing anything - always plan first, then ask for confirmation
This is a live data and you are analyst / personal assistant automating tasks
Never update or delete anything without confirmation and a report before after (like a dry run)

Use credentials from .env to access Shopify and S3 (picture storage)
Use Email credentinals (SMTP) to send emails if needed
Use Sendy credentials (API) to create and upload newsletter, cleanup tasks etc (https://sendy.co/api?app_path=https://mail.sinclairpatterns.com)

All Docs and MD files need to be placed to Docs fodler
All Tests belong in Tests fodler
All scripts like - Sendy_connector, Sendy_test_connection etc should be in Scripts
All Samples are stored on Samples folder (for example, Newsletters of different types)

If I give a big instruction to follow (like where to store files or data of a certain type - ask me if you need to update claude document with instructions).


To get a current admin api key for SHOPIFY - request it using this command and
curl -X POST "SHOPIFY_SHOP_URL/admin/oauth/access_token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=SHOPIFY_API_KEY" \
  -d "client_secret=SHOPIFY_API_SECRET"

  Store it in a session or in a text file. It expires in 24 hours.




Shopify API - working with segments https://shopify.dev/docs/apps/build/marketing-analytics/customer-segments/manage
