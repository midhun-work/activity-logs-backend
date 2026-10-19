from django.contrib.auth import get_user_model
from django.test import Client, TransactionTestCase, override_settings

from activity_logs import conf
from activity_logs.models import ActivityLog
from activity_logs.recorder import log_event
from tests.testapp.models import Note


def clear_conf_cache():
    for cached in (conf.skip_apps, conf.skip_models, conf.mask_fields, conf.hook):
        cached.cache_clear()


class LogTests(TransactionTestCase):
    def setUp(self):
        clear_conf_cache()
        user_model = get_user_model()
        self.staff = user_model.objects.create_user("ann", password="x", first_name="Ann", is_staff=True)
        self.other = user_model.objects.create_user("bob", password="x")
        self.client = Client()
        self.client.force_login(self.staff)

    def tearDown(self):
        clear_conf_cache()

    def rows(self, **filters):
        return ActivityLog.objects.filter(model="testapp.Note", **filters)

    def test_create_is_logged_with_who_and_masked_secret(self):
        self.client.post("/notes/", {"title": "First", "secret": "hunter2"}, HTTP_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0")
        row = self.rows(action="create").get()
        self.assertEqual(row.user_name, "Ann")
        self.assertEqual(row.new_data["title"], "First")
        self.assertEqual(row.new_data["secret"], "***")
        self.assertEqual((row.os, row.browser), ("Windows 10/11", "Chrome"))

    def test_update_keeps_only_changed_fields_and_a_secret_change_is_noticed(self):
        note = Note.objects.create(title="A", secret="one")  # no signed-in user: not logged
        self.assertEqual(self.rows().count(), 0)
        self.client.post(f"/notes/{note.pk}/", {"title": "B"})
        row = self.rows(action="update").get()
        self.assertEqual(row.changed_fields, ["title"])
        self.assertEqual(row.old_data, {"title": "A"})
        self.client.post(f"/notes/{note.pk}/", {"secret": "two"})
        row = self.rows(action="update").latest("id")
        self.assertEqual(row.changed_fields, ["secret"])
        self.assertEqual(row.new_data, {"secret": "***"})

    def test_a_save_that_changes_nothing_is_not_logged(self):
        note = Note.objects.create(title="A")
        self.client.post(f"/notes/{note.pk}/", {"title": "A"})
        self.assertEqual(self.rows().count(), 0)

    @override_settings(LOGS={"PAGE_SIZE": 2, "OBJECT_LABEL": "tests.hooks.object_label"})
    def test_object_label_hook_is_saved(self):
        clear_conf_cache()
        self.client.post("/notes/", {"title": "T", "phone": "9876543210"})
        self.assertEqual(self.rows(action="create").get().object_label, "9876543210")

    def test_log_event_writes_a_sign_in_row(self):
        log_event("login", "Signed in", user=self.staff)
        row = ActivityLog.objects.get(action="login")
        self.assertEqual((row.user_name, row.description), ("Ann", "Signed in"))

    def test_api_lists_pages_filters_and_blocks_non_staff(self):
        for i in range(3):
            self.client.post("/notes/", {"title": f"N{i}"})
        listing = self.client.get("/api/logs/").json()
        self.assertEqual((listing["total"], len(listing["results"]), listing["pages"]), (3, 2, 2))
        self.assertEqual(self.client.get("/api/logs/?q=nothing-matches").json()["total"], 0)
        row_id = listing["results"][0]["id"]
        self.assertIn("new_data", self.client.get(f"/api/logs/{row_id}/").json())
        self.assertEqual(self.client.get("/api/logs/meta/").json()["models"], ["testapp.Note"])

        outsider = Client()
        outsider.force_login(self.other)
        self.assertEqual(outsider.get("/api/logs/").status_code, 403)
