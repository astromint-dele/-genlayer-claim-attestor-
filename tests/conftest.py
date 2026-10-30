"""Windows shim for genlayer-test 0.29.2 direct mode.

gltest.direct.loader._inject_message_to_fd0 writes calldata to a temp file,
dup2()s it onto stdin and then unlinks it while still open. POSIX allows that;
Windows raises PermissionError (WinError 32). On Windows only, defer that
delete to the end of the session. No effect on Linux/macOS.
"""
import functools
import os
import sys

if sys.platform == "win32":
    import gltest.direct.loader as _loader

    _pending: list[str] = []
    _real_unlink = os.unlink
    _real_inject = _loader._inject_message_to_fd0

    def _lenient_unlink(path, *a, **kw):
        try:
            _real_unlink(path, *a, **kw)
        except PermissionError:
            _pending.append(path)

    @functools.wraps(_real_inject)
    def _inject(*a, **kw):
        os.unlink = _lenient_unlink
        try:
            return _real_inject(*a, **kw)
        finally:
            os.unlink = _real_unlink

    _loader._inject_message_to_fd0 = _inject

    def pytest_sessionfinish(session, exitstatus):
        for p in _pending:
            try:
                _real_unlink(p)
            except OSError:
                pass
