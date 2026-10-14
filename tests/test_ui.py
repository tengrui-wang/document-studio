import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from document_studio.app import MainWindow
from document_studio.storage import Settings


def test_all_pages_construct_without_api(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(Settings(tmp_path))
    assert window.stack.count() == 8
    assert window.translate.model.currentData() is None
    for index in range(8):
        window.nav.setCurrentRow(index)
        app.processEvents()
        assert window.stack.currentIndex() == index
    window.close()


def test_glossary_persists_and_update_controls_are_wired(tmp_path):
    app = QApplication.instance() or QApplication([])
    settings = Settings(tmp_path)
    settings.data["glossary"] = "term = 术语"
    settings.data["translation_preferences"] = {"chunk_size": 600, "source_lang": "English", "target_lang": "Chinese"}
    settings.save()
    window = MainWindow(settings)
    assert window.translate.glossary.toPlainText() == "term = 术语"
    assert window.translate.chunk.value() == 600
    assert not window.preferences.install_button.isEnabled()
    assert not window.preferences.download_button.isEnabled()
    window.translate.glossary.setPlainText("new = 新")
    assert window.translate.save_preferences()
    assert Settings(tmp_path).data["glossary"] == "new = 新"
    window.close()
