"""Offline checks on the progress-bar helper."""

from fastcat.utils import print_progress_bar


def test_progress_bar_renders_percentage_and_fill(capsys):
    print_progress_bar(5, 10, prefix='Progress:', suffix='Complete', length=10)

    out = capsys.readouterr().out
    assert '50.0%' in out
    assert '#####-----' in out
    assert 'Progress:' in out
    assert 'Complete' in out


def test_progress_bar_ends_the_line_when_complete(capsys):
    print_progress_bar(10, 10, length=10)

    out = capsys.readouterr().out
    assert '100.0%' in out
    assert out.endswith('\n')


def test_progress_bar_starts_empty(capsys):
    print_progress_bar(0, 10, length=10)

    out = capsys.readouterr().out
    assert '0.0%' in out
    assert '----------' in out
