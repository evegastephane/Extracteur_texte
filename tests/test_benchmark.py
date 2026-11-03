from scripts.benchmark import character_error


def test_character_error_counts_edits():
    assert character_error("chat", "chats") == .25
    assert character_error("chat", "chut") == .25
    assert character_error("chat", "cha") == .25
    assert character_error("école\r\ntexte", "e\u0301cole\ntexte") == 0
    assert character_error("école", "ecole") == .2
