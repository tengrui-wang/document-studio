"""Optional native Windows Credential Manager roundtrip with a dummy credential."""
import uuid
from document_studio.storage import Credentials

vault = Credentials()
identifier = "selftest-" + uuid.uuid4().hex
dummy = "document-studio-synthetic-credential"
try:
    vault.set(identifier, dummy)
    assert vault.get(identifier) == dummy
    print("WINDOWS_CREDENTIAL_ROUNDTRIP_OK")
finally:
    vault.delete(identifier)
