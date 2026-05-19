from sales_tax_tracker.settings import *  # noqa: F401, F403

SECRET_KEY = "test-secret-key"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

RUSTFS_ENDPOINT_URL = "http://test-rustfs:9000"
RUSTFS_PUBLIC_ENDPOINT_URL = "http://test-rustfs-public:9000"
RECEIPT_LLM_RESPONSES_URL = "http://test-llm:4000/v1/responses"
RECEIPT_LLM_API_KEY = "test-api-key"
RECEIPT_LLM_MODEL = "gpt-4o"
RECEIPT_LLM_TIMEOUT_SECONDS = 120
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
