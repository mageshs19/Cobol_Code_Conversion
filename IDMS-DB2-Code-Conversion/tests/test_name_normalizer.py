from idms_db2_phase2.services.name_normalizer import NameNormalizer


def test_normalize_replaces_hyphen_with_underscore():
    assert NameNormalizer.normalize("VMB-FAR") == "VMB_FAR"


def test_to_cobol_replaces_underscore_with_hyphen():
    assert NameNormalizer.to_cobol("NR_ID_479_FAR") == "NR-ID-479-FAR"


def test_remove_record_suffix_removes_four_digit_suffix():
    assert NameNormalizer.remove_record_suffix("FIELD_NAME_0410") == "FIELD_NAME"


def test_compact_removes_non_alphanumeric_characters():
    assert NameNormalizer.compact("DZ-BFAR_TV") == "DZBFARTV"


def test_normalize_none_returns_empty_string():
    assert NameNormalizer.normalize(None) == ""