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
