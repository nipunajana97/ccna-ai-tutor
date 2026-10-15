from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def by_label(elements, label):
    return next(element for element in elements if element.label == label)


def test_local_demo_trial_answer_and_fresh_session_paywall(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.delenv("RENDER", raising=False)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
    assert not app.exception
    by_label(app.button, "Generate my scenario").click().run()
    assert not app.exception
    assert by_label(app.button, "Generate my scenario").disabled
    assert app.radio
    app.radio[0].set_value(0)
    by_label(app.button, "Check my answer").click().run()
    assert not app.exception
    assert by_label(app.button, "Check my answer").disabled
    fresh = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
    assert not fresh.exception
    assert by_label(fresh.button, "Generate my scenario").disabled
    assert fresh.chat_input[0].disabled
