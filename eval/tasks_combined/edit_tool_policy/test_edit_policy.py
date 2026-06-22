from edit_policy import edit_tool_for_scope


def test_multiline_python_function_edits_use_ast_edit():
    assert edit_tool_for_scope("multi_line") == "ast_edit"


def test_single_line_edits_use_edit_file():
    assert edit_tool_for_scope("single_line") == "edit_file"
