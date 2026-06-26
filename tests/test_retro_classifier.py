from lib.retro.classifier import classify_error, is_error_content


def test_file_not_found():
    assert classify_error("bash: ENOENT: no such file or directory") == "FILE_NOT_FOUND"


def test_command_not_found():
    assert classify_error("zsh: command not found: foo") == "COMMAND_NOT_FOUND"


def test_user_rejected():
    assert classify_error("The user doesn't want to proceed (auto-denied)") == "USER_REJECTED"


def test_timeout():
    assert classify_error("Error: deadline exceeded, timed out after 60s") == "TIMEOUT"


def test_first_match_wins_order():
    # "No such file" deve vincere su "Error:" generico
    assert classify_error("Error: No such file or directory") == "FILE_NOT_FOUND"


def test_unknown_when_no_pattern():
    assert classify_error("tutto ok, nessun problema qui") == "UNKNOWN"


def test_is_error_true_on_indicator():
    assert is_error_content("Traceback (most recent call last): ...") is True


def test_is_error_false_on_short_or_clean():
    assert is_error_content("ok") is False
    assert is_error_content("Operazione completata con successo, 3 file scritti.") is False
