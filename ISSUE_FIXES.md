# Lumora Backend - Issue Fixes

## Issue 1: Image Upload Failure in News/Events Admin

### Root Cause

The admin panel fails to create news/events when images are attached. This is likely due to:

1. Cloudinary configuration warnings during startup
2. Potential issues with how Django admin handles file uploads with Cloudinary

### Solution

The issue appears to be that while Cloudinary is configured, there might be a race condition or initialization issue. Let's add explicit error handling:

**Fix for News Admin** (`news/admin.py`):

```python
def save_model(self, request, obj, form, change):
    if not obj.author:
        obj.author = request.user
    try:
        super().save_model(request, obj, form, change)
    except Exception as e:
        from django.contrib import messages
        messages.error(request, f"Failed to save news: {str(e)}")
        raise
```

**Fix for Events Admin** (`events/admin.py`):

```python
def save_model(self, request, obj, form, change):
    try:
        super().save_model(request, obj, form, change)
    except Exception as e:
        from django.contrib import messages
        messages.error(request, f"Failed to save event: {str(e)}")
        raise
```

### Alternative: Check Cloudinary Credentials

Verify in `.env` file:

```
CLOUDINARY_CLOUD_NAME=dsrepnl1c
CLOUDINARY_API_KEY=<your_key>
CLOUDINARY_API_SECRET=<your_secret>
```

---

## Issue 2: Random 401 Unauthorized Errors

### Root Cause

JWT access tokens expire after 1 day (`ACCESS_TOKEN_LIFETIME': timedelta(days=1)`). When tokens expire:

- User gets 401 errors
- Must log out and log back in to get new token
- This happens "randomly" (actually when 24 hours pass)

### Solution Options

**Option 1: Increase Token Lifetime** (Quick Fix)

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),  # Changed from 1 to 7 days
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

**Option 2: Implement Token Refresh** (Better Solution)
Enable automatic token refresh in the Flutter app:

1. Store both access and refresh tokens
2. When getting 401, try to refresh the access token
3. Only log out if refresh fails

**Option 3: Enable Token Rotation** (Most Secure)

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=5),  # Shorter access token
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,  # Changed to True
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
}
```

### Recommended: Option 1 + Frontend Fix

1. Increase token lifetime to 7 days (reduces frequency)
2. Add token refresh logic in Flutter app for when it does expire

---

## Issue 3: Mobile Keyboard Pushing Up Screen

### Root Cause

This is a common mobile web/admin issue where the keyboard overlays content and pushes the viewport up.

### Solution

Add viewport meta tag and CSS fixes to admin templates:

**Create** `templates/admin/base_site.html`:

```html
{% extends "admin/base.html" %} {% block extrahead %} {{ block.super }}
<meta
  name="viewport"
  content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"
/>
<style>
  /* Fix for mobile keyboard issues */
  @media (max-width: 768px) {
    body {
      position: fixed;
      width: 100%;
    }

    #content {
      overflow-y: auto;
      -webkit-overflow-scrolling: touch;
    }

    /* Prevent zoom on input focus */
    input,
    select,
    textarea {
      font-size: 16px !important;
    }
  }
</style>
{% endblock %}
```

**Update** `settings.py`:

```python
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, 'templates')],  # Already set
        "APP_DIRS": True,
        ...
    },
]
```

---

## Implementation Priority

1. **401 Errors** (High Priority - affects all users)

   - Quick fix: Increase token lifetime to 7 days
   - Long-term: Implement token refresh in Flutter app

2. **Image Upload** (High Priority - blocks content creation)

   - Add error handling to admin
   - Verify Cloudinary credentials
   - Test with small image first

3. **Mobile Keyboard** (Medium Priority - UX issue)
   - Add custom admin template
   - Test on actual mobile device

---

## Testing Commands

### Test Image Upload

```bash
# From Django admin panel:
1. Go to /admin/news/news/add/
2. Fill in title and content
3. Upload a small test image (< 1MB)
4. Check browser console for errors
5. Check Django logs for Cloudinary errors
```

### Test Token Expiry

```bash
# In Flutter app or API client:
1. Login and save token
2. Wait 24+ hours OR manually expire token
3. Try to access protected endpoint
4. Should get 401 error
5. After fix: should work for 7 days
```

### Test Mobile Keyboard

```bash
# On mobile device:
1. Open admin panel on mobile browser
2. Navigate to push notification form
3. Tap on text input field
4. Keyboard should not push content off screen
```
