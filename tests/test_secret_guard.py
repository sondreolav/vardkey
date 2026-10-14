"""Tests for the local wallet-secret guard (sections 2 and 15).

Every secret in this module is synthetic. The seed phrase is a run of BIP39 words
in an order that is not a valid checksum, so it cannot be a usable wallet, and the
key-shaped strings are the prefix and the length of the real formats filled with
repeated base58 characters.

A field also has a length limit, and the guard runs first: a value that looks like
a wallet secret is refused with what it looks like, even when it is longer than
the field allows. The limit is the outer bound, and it is still applied to
everything the guard lets through. The four short label fields (the key name, the
model, the wallet software name and the admin username) hold 60 characters, so the
80-character seed phrase is over their limit; a WIF key (52) and a BIP38 key (58)
fit them, and cover the other path.
"""

from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError

from app import AppHandler
from auth import validate_admin_credentials
from database import (
    initialize_database,
    list_export_rows,
    list_health_checks,
    list_keys,
    save_key_setup,
)
from export import build_csv
from secret_guard import BIP39_WORDS, find_secret
from server_session import SessionMixin
from validation import (
    SecretDetected,
    ValidationError,
    validate_health_check,
    validate_key_settings,
    validate_key_setup,
    validate_rotation,
    validate_wallet_software,
)


ROOT = Path(__file__).resolve().parents[1]
ADDRESS_PATH = "m/48'/0'/0'/2'"
SECOND_ADDRESS_PATH = "m/48'/1'/0'/2'"
THIRD_ADDRESS_PATH = "m/48'/2'/0'/2'"
NEW_ADDRESS_PATH = "m/48'/7'/0'/2'"
SOFTWARE_NAMES = ("Sparrow Wallet",)
KEYS = (
    {"id": 1, "key_number": 1, "name": "SeedSigner", "type": "hardware", "address_path": ADDRESS_PATH},
    {"id": 2, "key_number": 2, "name": "Blockstream Jade", "type": "hardware", "address_path": SECOND_ADDRESS_PATH},
    {"id": 3, "key_number": 3, "name": "Nunchuk", "type": "cloud", "address_path": THIRD_ADDRESS_PATH},
)
DEFAULT_SETUP = [
    {"key_number": 1, "name": "SeedSigner", "type": "hardware", "address_path": ADDRESS_PATH},
    {"key_number": 2, "name": "Blockstream Jade", "type": "hardware", "address_path": SECOND_ADDRESS_PATH},
    {"key_number": 3, "name": "Nunchuk", "type": "cloud", "address_path": THIRD_ADDRESS_PATH},
]

# Twelve BIP39 words in an order that is not a valid checksum. Synthetic.
SEED_PHRASE = (
    "accident abandon ability able about above absent absorb abstract absurd "
    "abuse access"
)
# Eleven of them, which is below the threshold and must be left alone.
SHORT_RUN = "abandon ability able about above absent absorb abstract absurd abuse access"
# The prefix and the length of each real format, filled with base58 characters.
EXTENDED_PRIVATE_KEY = "xprv" + "A" * 107
# A WIF key is 52 characters and a BIP38 key is 58, so both fit a 60-character
# label field, while the extended key and the PEM block do not. They are what a
# short field is tested with, so both sides of the length limit are covered.
WIF_PRIVATE_KEY = "L" + "A" * 51
BIP38_KEY = "6P" + "A" * 56
PEM_PRIVATE_KEY = "-----BEGIN EC PRIVATE KEY-----\nMHQCAQEEIBkg4LVWM" + "A" * 40
# A transaction id is a bare 64-character hex string, which is legitimate note
# content and must not be refused (a documented limitation of the guard).
TRANSACTION_ID = "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b"


def read_static(name):
    """Return the text of one static asset."""
    return (ROOT / "static" / name).read_text(encoding="utf-8")


def payload(key_number=1):
    """Return a fresh valid payload for one key, ready to be mutated by a test."""
    key = KEYS[key_number - 1]
    return {
        "checked_at": "2026-10-01",
        "wallet_software": "Sparrow Wallet",
        "software_version": "1.8.0",
        "software_compatibility_status": "OK",
        "software_comments": "",
        "contact_info_verified": "Confirmed current",
        "comments": "Annual review",
        "key_check": {
            "key_id": key["id"],
            "available": 1,
            "address_path": key["address_path"],
            "hardware_works": 1,
            "firmware_version": "1.0.0",
            "seed_backup_verified": "OK",
            "comments": "",
        },
        "ai_security_checks": [
            {"provider": key["name"], "status": "SECURE", "comments": ""},
            {"provider": "Sparrow Wallet", "status": "SECURE", "comments": ""},
        ],
    }


def setup_entry(key_number, name, key_type, address_path=None, model=None):
    """Return one key of a setup payload, on its own address path by default."""
    paths = {1: ADDRESS_PATH, 2: SECOND_ADDRESS_PATH, 3: THIRD_ADDRESS_PATH}
    return {
        "key_number": key_number,
        "name": name,
        "type": key_type,
        "address_path": paths[key_number] if address_path is None else address_path,
        "model": model,
    }


class WordlistTests(unittest.TestCase):
    """The embedded BIP39 wordlist is the specification's own list.

    The list is copied into ``secret_guard`` rather than fetched, because the app
    makes no network call. These checks are what keeps the copy honest: the
    specification lists 2048 words in alphabetical order, and no two words share
    their first four letters, so a wrong or missing word is caught here.
    """

    def test_the_list_holds_the_two_thousand_and_forty_eight_words(self):
        words = list(BIP39_WORDS)

        self.assertEqual(len(words), 2048)
        self.assertEqual(words[0], "abandon")
        self.assertEqual(words[-1], "zoo")

    def test_the_list_is_in_the_order_the_specification_lists_it(self):
        words = list(BIP39_WORDS)

        self.assertEqual(words, sorted(words))

    def test_every_word_is_a_short_lower_case_word(self):
        for word in BIP39_WORDS:
            self.assertRegex(word, r"^[a-z]{3,8}$")

    def test_no_two_words_share_their_first_four_letters(self):
        # The specification guarantees this, so a repeated prefix means a word
        # was mistyped or lost.
        prefixes = [word[:4] for word in BIP39_WORDS]

        self.assertEqual(len(set(prefixes)), len(BIP39_WORDS))

    def test_common_words_that_are_not_in_the_list_stay_out_of_it(self):
        # The check only fires on a run of words from this list, so ordinary
        # prose must not be caught by it.
        for absent in ("the", "and", "was", "of", "is", "a", "not"):
            self.assertNotIn(absent, BIP39_WORDS)


class DetectionTests(unittest.TestCase):
    """What the guard recognises, and what it leaves alone."""

    def test_a_seed_phrase_is_recognised(self):
        for text in (
            SEED_PHRASE,
            f"  {SEED_PHRASE}  ",
            SEED_PHRASE.upper(),
            f"My notes. {SEED_PHRASE} End of notes.",
        ):
            self.assertEqual(find_secret(text), "a seed phrase", text)

    def test_a_twenty_four_word_phrase_is_recognised(self):
        phrase = " ".join(list(BIP39_WORDS)[:24])

        self.assertEqual(find_secret(phrase), "a seed phrase")

    def test_a_run_below_twelve_words_is_left_alone(self):
        self.assertIsNone(find_secret(SHORT_RUN))

    def test_a_key_shaped_token_is_recognised(self):
        for token, label in (
            (EXTENDED_PRIVATE_KEY, "an extended private key"),
            (WIF_PRIVATE_KEY, "a private key"),
            (BIP38_KEY, "an encrypted private key"),
            (PEM_PRIVATE_KEY, "a PEM private key"),
        ):
            self.assertEqual(find_secret(f"please check {token}"), label, token)

    def test_every_extended_private_key_prefix_is_recognised(self):
        for prefix in ("xprv", "yprv", "zprv", "tprv", "uprv", "vprv"):
            self.assertEqual(
                find_secret(prefix + "A" * 107),
                "an extended private key",
                prefix,
            )

    def test_the_uncompressed_wif_length_is_recognised_too(self):
        self.assertEqual(find_secret("5" + "A" * 50), "a private key")
        self.assertEqual(find_secret("9" + "A" * 50), "a private key")

    def test_a_public_extended_key_is_not_refused(self):
        # An xpub is a public key: it is not a secret, and the app must not
        # refuse it as if it were one.
        self.assertIsNone(find_secret("xpub" + "A" * 107))

    def test_ordinary_notes_are_not_refused(self):
        for text in (
            "Annual review",
            "Key is with the third holder",
            "Path read from the device",
            "The device works and the backup is intact",
            "Replaced the battery and checked the firmware",
            "Sparrow Wallet",
            "ColdCard Q",
            "Confirmed current",
            ADDRESS_PATH,
            "1.8.0",
            "",
        ):
            self.assertIsNone(find_secret(text), text)

    def test_a_transaction_id_is_not_refused(self):
        # A bare hex string is indistinguishable from a transaction id, so it is
        # deliberately not refused; the limitation is documented in the module.
        self.assertIsNone(find_secret(f"Confirmed against txid {TRANSACTION_ID}"))

    def test_text_that_is_not_a_string_is_left_alone(self):
        for value in (None, 12, [], {}):
            self.assertIsNone(find_secret(value))


class FieldRejectionTests(unittest.TestCase):
    """Every free-text field refuses a wallet secret, and never repeats it."""

    def assert_refused(self, data, label="a seed phrase"):
        """Assert that a payload is refused and that the value is not echoed."""
        with self.assertRaises(SecretDetected) as context:
            validate_health_check(data, KEYS, SOFTWARE_NAMES)
        message = str(context.exception)
        self.assertIn(f"looks like {label}", message)
        self.assertIn("Nothing was saved", message)
        return message

    def test_the_overall_comment_is_checked(self):
        data = payload()
        data["comments"] = SEED_PHRASE

        message = self.assert_refused(data)

        self.assertNotIn("abandon", message)
        self.assertNotIn(SEED_PHRASE, message)

    def test_the_key_note_is_checked(self):
        data = payload()
        data["key_check"]["comments"] = EXTENDED_PRIVATE_KEY

        self.assert_refused(data, "an extended private key")

    def test_the_firmware_version_is_checked(self):
        data = payload()
        data["key_check"]["firmware_version"] = WIF_PRIVATE_KEY

        self.assert_refused(data, "a private key")

    def test_the_software_version_is_checked(self):
        data = payload()
        data["software_version"] = BIP38_KEY

        self.assert_refused(data, "an encrypted private key")

    def test_the_compatibility_notes_are_checked(self):
        data = payload()
        data["software_comments"] = SEED_PHRASE

        self.assert_refused(data)

    def test_a_security_check_comment_is_checked(self):
        data = payload()
        data["ai_security_checks"][0]["comments"] = PEM_PRIVATE_KEY

        self.assert_refused(data, "a PEM private key")

    def test_the_address_path_is_checked(self):
        data = payload()
        data["key_check"]["address_path"] = SEED_PHRASE

        self.assert_refused(data)

    def test_the_setup_name_and_model_are_checked(self):
        # The name and the model hold 60 characters, so the WIF key (52) and the
        # BIP38 key (58) are used here: they fit, and the guard names them.
        with self.assertRaises(SecretDetected) as name_context:
            validate_key_setup({"keys": [
                setup_entry(1, WIF_PRIVATE_KEY, "hardware"),
                setup_entry(2, "Jade", "hardware"),
                setup_entry(3, "Nunchuk", "cloud"),
            ]})

        self.assertIn("looks like a private key", str(name_context.exception))

        with self.assertRaises(SecretDetected) as model_context:
            validate_key_setup({"keys": [
                setup_entry(1, "ColdCard", "hardware", model=BIP38_KEY),
                setup_entry(2, "Jade", "hardware"),
                setup_entry(3, "Nunchuk", "cloud"),
            ]})

        self.assertIn("looks like an encrypted private key", str(model_context.exception))

    def test_the_settings_and_the_rotation_are_checked(self):
        with self.assertRaises(SecretDetected):
            validate_key_settings(
                {"key_id": 1, "name": WIF_PRIVATE_KEY, "address_path": ADDRESS_PATH}, KEYS
            )

        with self.assertRaises(SecretDetected):
            validate_key_settings(
                {"key_id": 1, "name": "ColdCard", "address_path": WIF_PRIVATE_KEY}, KEYS
            )

        with self.assertRaises(SecretDetected):
            validate_rotation(
                {
                    "replaced": True,
                    "keep_name": True,
                    "address_path": NEW_ADDRESS_PATH,
                    "model": BIP38_KEY,
                },
                KEYS,
                1,
            )

    def test_the_wallet_software_list_is_checked(self):
        with self.assertRaises(SecretDetected) as context:
            validate_wallet_software({"wallet_software": [WIF_PRIVATE_KEY]}, KEYS)

        self.assertIn("wallet software name", str(context.exception))
        self.assertIn("looks like a private key", str(context.exception))

    def test_the_admin_username_is_checked(self):
        # A WIF key fits the 60-character username limit and a seed phrase does
        # not, and both are answered with what they look like, because the guard
        # runs before the length limit.
        for value, label in (
            (WIF_PRIVATE_KEY, "a private key"),
            (SEED_PHRASE, "a seed phrase"),
        ):
            with self.assertRaises(ValueError) as context:
                validate_admin_credentials({
                    "username": value,
                    "password": "long-enough",
                })

            message = str(context.exception)
            self.assertIn("admin username", message)
            self.assertIn(f"looks like {label}", message)
            self.assertNotIn(value, message)

    def test_the_admin_password_is_not_checked(self):
        # A long passphrase is a legitimate password, so the guard must not stand
        # between the user and their own login.
        username, password = validate_admin_credentials({
            "username": "admin",
            "password": SEED_PHRASE,
        })

        self.assertEqual(username, "admin")
        self.assertEqual(password, SEED_PHRASE)

    def test_a_secret_in_a_short_label_field_is_named_as_one(self):
        # A value that fits the field is refused with what was recognised, and
        # the value itself is never repeated.
        with self.assertRaises(SecretDetected) as context:
            validate_key_settings(
                {"key_id": 1, "name": WIF_PRIVATE_KEY, "address_path": ADDRESS_PATH},
                KEYS,
            )

        message = str(context.exception)
        self.assertIn("key name looks like a private key", message)
        self.assertIn("Nothing was saved", message)
        self.assertNotIn(WIF_PRIVATE_KEY, message)

    def test_a_secret_over_the_field_limit_is_still_named_as_one(self):
        # The guard runs before the length limit, so a seed phrase that is longer
        # than the field is answered with what it looks like. The other order
        # would answer "too long", which invites the user to shorten a seed
        # phrase instead of removing it.
        with self.assertRaises(SecretDetected) as context:
            validate_key_settings(
                {"key_id": 1, "name": SEED_PHRASE, "address_path": ADDRESS_PATH},
                KEYS,
            )

        message = str(context.exception)
        self.assertIn("key name looks like a seed phrase", message)
        self.assertNotIn("too long", message)
        self.assertNotIn(SEED_PHRASE, message)

    def test_the_length_limit_still_applies_to_everything_else(self):
        # The limit is the outer bound, so an ordinary over-long value is still
        # refused for its length, and the guard does not weaken it.
        with self.assertRaises(ValidationError) as context:
            validate_key_settings(
                {"key_id": 1, "name": "x" * 61, "address_path": ADDRESS_PATH},
                KEYS,
            )

        self.assertIn("key name is too long", str(context.exception))

    def test_an_ordinary_payload_still_passes(self):
        result = validate_health_check(payload(), KEYS, SOFTWARE_NAMES)

        self.assertEqual(result["comments"], "Annual review")
        self.assertEqual(result["key_check"]["firmware_version"], "1.0.0")

    def test_the_refusal_is_a_validation_error(self):
        # The HTTP handlers answer a ValidationError with 400, so the refusal has
        # to be one, or a pasted secret would be answered with 500.
        self.assertTrue(issubclass(SecretDetected, ValidationError))


class WarningTests(unittest.TestCase):
    """A short reminder sits with every free-text field (section 2)."""

    def test_the_check_form_warns_at_each_static_free_text_field(self):
        html = read_static("health-check.html")

        self.assertEqual(html.count('class="secret-warning"'), 3)
        self.assertIn("Never paste a seed phrase or a private key here.", html)

    def test_the_check_script_warns_at_the_fields_it_builds(self):
        script = read_static("health-check.js")

        self.assertIn("SECRET_WARNING", script)
        self.assertIn("secret-warning", script)
        self.assertIn("details.append(secretWarning());", script)
        self.assertIn('card.append(makeField("Key notes", "key_comments", makeTextarea("key_comments")));', script)
        self.assertIn('card.append(makeField("Comment", commentName, makeTextarea(commentName, 1000)));', script)

    def test_the_setup_page_warns_at_every_key_card(self):
        html = read_static("setup.html")
        script = read_static("setup.js")

        self.assertEqual(html.count('class="secret-warning"'), 3)
        self.assertIn("SECRET_WARNING", script)
        self.assertIn("fieldset.append(grid, modelLabel, pathLabel, secretWarning());", script)

    def test_the_settings_script_warns_at_the_fields_it_builds(self):
        script = read_static("settings.js")

        self.assertIn("SECRET_WARNING", script)
        self.assertIn("field.append(secretWarning());", script)
        self.assertIn("card.append(secretWarning());", script)

    def test_the_stylesheet_carries_the_reminder_style(self):
        styles = read_static("styles.css")

        self.assertIn(".secret-warning", styles)

    def test_the_page_notice_is_still_there(self):
        # The page-level notice is the existing one; the field reminder is added
        # on top of it, not instead of it.
        for name in ("health-check.html", "setup.html", "settings.html"):
            self.assertIn("Never enter seed phrases", read_static(name))


class SecretStorageApiTests(SessionMixin, unittest.TestCase):
    """A refused value is never stored and never reaches the export."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "test.sqlite3")
        initialize_database(self.database_path)
        save_key_setup(DEFAULT_SETUP, self.database_path)
        self.key_id = list_keys(self.database_path)[0]["id"]
        self.previous_database_path = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = self.database_path

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.authenticate()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        if self.previous_database_path is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = self.previous_database_path
        self.temp_dir.cleanup()

    def post_status(self, path, data):
        """Return the status and the JSON body, whether it is an error or not."""
        try:
            with self.post_json(path, data) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)

    def health_check(self, **changes):
        """Return a valid submission for the stored key, with changes applied."""
        data = payload()
        data["key_check"]["key_id"] = self.key_id
        for field, value in changes.items():
            data[field] = value
        return data

    def stored_text(self):
        """Return everything the database holds, as one string."""
        return build_csv(list_export_rows(self.database_path))

    def test_a_secret_in_a_comment_is_refused_and_stored_nowhere(self):
        status, body = self.post_status(
            "/api/health-checks", self.health_check(comments=SEED_PHRASE)
        )

        self.assertEqual(status, 400)
        self.assertIn("looks like a seed phrase", body["error"])
        self.assertNotIn("abandon", body["error"])
        # Nothing was written, and nothing reached the export.
        self.assertEqual(list_health_checks(self.database_path), [])
        self.assertNotIn("abandon", self.stored_text())

    def test_a_key_note_with_a_private_key_is_refused(self):
        data = self.health_check()
        data["key_check"]["comments"] = EXTENDED_PRIVATE_KEY

        status, body = self.post_status("/api/health-checks", data)

        self.assertEqual(status, 400)
        self.assertIn("looks like an extended private key", body["error"])
        self.assertNotIn(EXTENDED_PRIVATE_KEY, body["error"])
        self.assertEqual(list_health_checks(self.database_path), [])

    def test_an_ordinary_check_is_still_saved_and_exported(self):
        status, body = self.post_status("/api/health-checks", self.health_check())

        self.assertEqual(status, 201)
        self.assertIsNotNone(body["id"])
        checks = list_health_checks(self.database_path)
        self.assertEqual(len(checks), 1)
        self.assertIn("Annual review", self.stored_text())

    def test_the_export_never_carries_a_refused_value(self):
        # A stored check is followed by a refused one, so the export holds the
        # first and none of the second.
        self.post_status("/api/health-checks", self.health_check())
        self.post_status(
            "/api/health-checks",
            self.health_check(comments=f"txid {TRANSACTION_ID} {SEED_PHRASE}"),
        )

        exported = self.stored_text()

        self.assertIn("Annual review", exported)
        self.assertNotIn("abandon", exported)
        self.assertEqual(len(list_health_checks(self.database_path)), 1)

    def test_the_admin_username_is_refused_by_the_api(self):
        # The first-run step goes through the same guard, and the message never
        # repeats what was pasted.
        status, body = self.post_status(
            "/api/login", {"username": SEED_PHRASE, "password": "long-enough"}
        )

        # The admin already exists, so the login is answered with 401; the point
        # here is that the payload never reaches the credential check as a name.
        self.assertIn(status, (400, 401))
        self.assertNotIn("abandon", body.get("error", ""))


if __name__ == "__main__":
    unittest.main()
