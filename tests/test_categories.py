"""End-to-end category lookups against a real Redis instance.

Marked ``integration``: each language downloads its SKOS dump from DBpedia and
loads it into Redis. Run with ``pytest --run-integration``.
"""

import pytest

from language_cases import LANGUAGE_CASES

pytestmark = pytest.mark.integration


def _case_id(case):
    return case.language


@pytest.mark.parametrize('case', LANGUAGE_CASES, ids=_case_id)
def test_language_is_loaded(loaded_fastcat, case):
    client = loaded_fastcat(case.language)
    assert client._is_loaded(language=case.language)


@pytest.mark.parametrize('case', LANGUAGE_CASES, ids=_case_id)
def test_broader(loaded_fastcat, case):
    client = loaded_fastcat(case.language)
    assert case.expected_broader in client.broader(case.broader_of)


@pytest.mark.parametrize('case', LANGUAGE_CASES, ids=_case_id)
def test_narrower(loaded_fastcat, case):
    client = loaded_fastcat(case.language)
    assert case.expected_narrower in client.narrower(case.narrower_of)


@pytest.mark.parametrize('case', LANGUAGE_CASES, ids=_case_id)
def test_current_language_is_resolvable(loaded_fastcat, case):
    client = loaded_fastcat(case.language)
    assert client.get_current_language() is not None
