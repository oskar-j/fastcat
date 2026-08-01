"""Offline checks on the language -> Redis db-slot bookkeeping."""

import pytest


def test_english_owns_slot_zero_on_first_run(isolated_store):
    assert isolated_store.get_slot('en') == 0


def test_unknown_language_raises(isolated_store):
    with pytest.raises(ValueError):
        isolated_store.get_slot('pl')


def test_new_languages_take_consecutive_slots(isolated_store):
    assert isolated_store.save_settings('pl') == 1
    assert isolated_store.save_settings('de') == 2
    assert isolated_store.get_slot('pl') == 1
    assert isolated_store.get_slot('de') == 2


def test_slots_survive_a_reload(isolated_store):
    isolated_store.save_settings('pl')

    isolated_store.languages.clear()
    isolated_store.load_settings()

    assert isolated_store.get_slot('pl') == 1


def test_language_is_resolvable_from_its_slot(isolated_store):
    isolated_store.save_settings('pl')

    assert isolated_store.get_language(slot=1).alpha_2.lower() == 'pl'


def test_unassigned_slot_resolves_to_none(isolated_store):
    assert isolated_store.get_language(slot=15) is None
