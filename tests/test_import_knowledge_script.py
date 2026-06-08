def test_import_knowledge_script_imports_current_rag_stack():
    from scripts import import_knowledge

    assert callable(import_knowledge.import_3c_knowledge)
