import sys


def test_import_yuxi_does_not_eagerly_import_knowledge(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    previous_yuxi = sys.modules.pop("yuxi", None)
    previous_knowledge = sys.modules.pop("yuxi.knowledge", None)

    try:
        import yuxi

        assert yuxi.get_version() == yuxi.__version__
        assert "yuxi.knowledge" not in sys.modules
    finally:
        sys.modules.pop("yuxi", None)
        sys.modules.pop("yuxi.knowledge", None)
        if previous_yuxi is not None:
            sys.modules["yuxi"] = previous_yuxi
        if previous_knowledge is not None:
            sys.modules["yuxi.knowledge"] = previous_knowledge
