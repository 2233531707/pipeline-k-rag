Yuxi Web static package

This package contains the built Vue static files for separated Web deployment.

Deployment summary:

1. Extract this zip to the external Nginx/CDN static root, for example:
   /var/www/yuxi-web
2. Configure the same public domain to serve static files and proxy /api to the
   backend API service.
3. Keep /api uncached and streaming-friendly. See nginx.example.conf.
4. Verify:
   https://app.example.com/
   https://app.example.com/api/system/health

The frontend keeps same-origin /api semantics. Do not edit built assets to point
to a separate API domain for the main deployment path.
