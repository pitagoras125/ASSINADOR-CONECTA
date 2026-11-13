import pytest
@pytest.fixture(autouse=True)
def no_network_update_checks(monkeypatch):
    # GUI tests must not contact the distribution channel.
    import sys
    monkeypatch.setattr(sys,"argv",["ConectaPDF"])
    import update_ui
    monkeypatch.setattr(update_ui,'check_update',lambda:None)
