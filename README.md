# geosys-activity-logs

Activity log for Django. Records who **created, changed or deleted** any record, and who **signed in or
out**, with the time, IP address, request, device (operating system and browser, read from the
User-Agent) and the values before and after. Read it through a small read-only API (and the Django
admin). The matching React screen is the npm package `@geosys/activity-logs`.

## What gets logged

- Any model's create / update / delete made by a **signed-in user's request** (signals).
  An update keeps only the fields that changed; a save that changes nothing is not logged.
- Sign-in / sign-out and anything else you report with `log_event(...)`.
- Not logged: changes from scripts or cron (no user), `queryset.update()` / `bulk_create()` (Django sends
  no signals for them), and the apps / models listed in `SKIP_APPS` / `SKIP_MODELS`.
- Fields in `MASK_FIELDS` are stored as `***` (a change to them is still recorded, without the values).
- A row is written only after the change is committed, so a rolled-back change leaves no log, and a
  logging error never breaks the save it describes.

## Install

```bash
pip install "git+https://github.com/midhun-work/activity-logs-backend.git@v0.1.0"
```

1. `INSTALLED_APPS += ["activity_logs"]` (its app label is `logs`, its table `logs_activitylog`).
2. Add the middleware **after** authentication (and after any tenant middleware):
   `MIDDLEWARE += ["activity_logs.middleware.RequestContextMiddleware"]`
3. Optional settings (defaults in `activity_logs/conf.py`):

   ```python
   LOGS = {
       "DATABASE": "default",
       "SKIP_APPS": ["logs", "sessions", "contenttypes", "admin", "migrations"],
       "SKIP_MODELS": ["auth.Permission"],
       "MASK_FIELDS": ["password", "token", "otp"],
       "USER_INFO": "myproject.log_hooks.user_info",          # user -> {type, id, name, phone, role}
       "TENANT": "myproject.log_hooks.current_tenant",        # () -> "shop-slug" or ""
       "OBJECT_LABEL": "myproject.log_hooks.object_label",    # record -> "9876543210" or ""
       "PERMISSION_CLASSES": ["rest_framework.permissions.IsAdminUser"],
       "PAGE_SIZE": 25,
       "MAX_PAGE_SIZE": 100,
   }
   ```

   `SKIP_APPS` uses app **labels**, so the package itself is listed as `"logs"`.

4. URLs: `path("api/", include("activity_logs.urls"))` gives `api/logs/`, `api/logs/<id>/`, `api/logs/meta/`.
5. `python manage.py migrate` (the migrations ship with the package).
6. Token sign-in (JWT etc.) does not fire Django's login signal, so log it where the token is issued:

   ```python
   from activity_logs.recorder import log_event
   log_event("login", "Signed in", user=user, request=request)
   ```

With several databases, keep the log table in one place (`DATABASE`) and route the `logs` app label there.

## API

`GET api/logs/?page=1&page_size=25&from=2026-10-01&to=2026-10-17&tenant=&action=&model=&user_type=&q=`
answers `{results, total, page, pages, page_size}`, newest first (`q` searches the user's name or phone,
the description, the record's label and the record id). `GET api/logs/<id>/` adds `old_data` and
`new_data`. `GET api/logs/meta/` gives the filter choices.

## Hooks (all optional)

- `USER_INFO(user)` returns `{type, id, name, phone, role}`. Without it the app reads `first_name`,
  `last_name`, `phone_number` and `role` off the user.
- `TENANT()` returns the shop / tenant of the current request, or `""`.
- `OBJECT_LABEL(instance)` returns a readable name for a changed record (for example a customer's
  phone), shown beside its id. Return `""` for models that have none.

## Test

```bash
pip install -e .
python -m django test tests --settings=tests.settings
```

## Release

Change `version` in `pyproject.toml`, commit, then `git tag v0.1.1 && git push --tags`.
Projects update by changing the tag in their requirements.
