from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "src" / "App.tsx"
TOOLBAR = ROOT / "frontend" / "src" / "components" / "Toolbar.tsx"
KNOWLEDGE_PANEL = ROOT / "frontend" / "src" / "components" / "KnowledgePanel.tsx"


def test_knowledge_management_is_top_level_page():
    app = APP.read_text(encoding="utf-8")
    toolbar = TOOLBAR.read_text(encoding="utf-8")
    panel = KNOWLEDGE_PANEL.read_text(encoding="utf-8")

    assert "type PageKey = 'chat' | 'knowledge'" in app
    assert "activePage" in app
    assert "聊天工作台" in toolbar
    assert "知识库管理" in toolbar
    assert "onPageChange" in toolbar

    main_layout = app[app.index('<div className="flex-1 flex min-h-0">') :]
    assert "activePage === 'chat'" in main_layout
    assert "activePage === 'knowledge'" in main_layout

    bottom_mount = app.split('<div className="flex-1 flex min-h-0">', 1)[-1]
    assert "</div>\n\n      <KnowledgePanel" not in bottom_mount
    assert 'className="flex-1 overflow-y-auto bg-gray-50/60"' in panel
