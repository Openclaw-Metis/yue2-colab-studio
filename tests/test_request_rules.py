import pytest

from yue2_studio import request_rules, ui_text
from yue2_studio.request_rules import AbcFileRejected, StudioRequest, ValidationFailed, validate


def fields(raw):
    with pytest.raises(ValidationFailed) as caught:
        validate(raw)
    return caught.value.fields


def test_minimal_request_gets_defaults_and_a_seed():
    request = validate({"style": "  piano pop  "})
    assert request.style == "piano pop"
    assert request.lyrics == ""
    assert request.cot == "full"
    assert 0 <= request.seed <= request_rules.SEED_MAX
    assert request.cfg_scale is None and request.abc is None


def test_blank_style_is_rejected():
    assert fields({"style": "   \n"}) == ["style"]


def test_empty_lyrics_are_accepted():
    assert validate({"style": "ambient", "lyrics": ""}).lyrics == ""


def test_abc_with_cot_off_is_rejected():
    assert fields({"style": "pop", "cot": "off", "abc": "X:1\nK:C\nC"}) == ["abc"]


@pytest.mark.parametrize("seed", [-1, 2**31, 1.5, "abc", True, float("nan")])
def test_bad_seeds_are_rejected(seed):
    assert fields({"style": "pop", "seed": seed}) == ["seed"]


@pytest.mark.parametrize("seed, expected", [(0, 0), (42.0, 42), ("7", 7), (2**31 - 1, 2**31 - 1)])
def test_good_seeds_are_kept(seed, expected):
    assert validate({"style": "pop", "seed": seed}).seed == expected


@pytest.mark.parametrize("blank", [None, "", "  "])
def test_blank_seed_means_random(blank):
    seeds = {validate({"style": "pop", "seed": blank}).seed for _ in range(5)}
    assert len(seeds) > 1


@pytest.mark.parametrize("cfg", [0.9, 2.1, "x", True, float("inf")])
def test_bad_cfg_is_rejected(cfg):
    assert fields({"style": "pop", "cfg_scale": cfg}) == ["cfg_scale"]


def test_cfg_in_range_is_kept():
    assert validate({"style": "pop", "cfg_scale": 1.2}).cfg_scale == 1.2


def test_unknown_cot_is_rejected():
    assert fields({"style": "pop", "cot": "chords"}) == ["cot"]


def test_lengths_are_reported_with_counts():
    with pytest.raises(ValidationFailed) as caught:
        validate({"style": "s" * 1001, "lyrics": "l" * 50000})
    messages = {error.field: error.message for error in caught.value.errors}
    assert "1001" in messages["style"]
    assert "50000" in messages["lyrics"]


def test_several_errors_are_collected_together():
    assert fields({"style": "", "seed": -5, "cot": "nope"}) == ["style", "cot", "seed"]


def test_blank_abc_becomes_none():
    assert validate({"style": "pop", "abc": "  \n "}).abc is None


def test_oversized_abc_is_rejected():
    assert fields({"style": "pop", "abc": "C" * (request_rules.ABC_BYTES_LIMIT + 1)}) == ["abc"]


def test_html_in_lyrics_is_kept_verbatim():
    lyrics = "[Verse]\n<script>alert(1)</script>"
    assert validate({"style": "pop", "lyrics": lyrics}).lyrics == lyrics


def test_request_round_trips_through_dict():
    request = validate({"style": "國語抒情", "lyrics": "[Verse]\n霓虹", "seed": 5, "cfg_scale": 1.5})
    assert StudioRequest.from_dict(request.to_dict()) == request


# --- uploaded scores ----------------------------------------------------------


def test_read_abc_file_normalises_newlines_and_bom(tmp_path):
    path = tmp_path / "tune.abc"
    path.write_bytes("﻿X:1\r\nK:C\r\nC D E\r\n".encode())
    assert request_rules.read_abc_file(path) == "X:1\nK:C\nC D E\n"


def test_txt_suffix_is_accepted(tmp_path):
    path = tmp_path / "tune.TXT"
    path.write_text("X:1\nK:C\nC", encoding="utf-8")
    assert request_rules.read_abc_file(path).startswith("X:1")


@pytest.mark.parametrize(
    "name, data, message",
    [
        ("tune.mid", b"MThd", ui_text.ABC_WRONG_TYPE),
        ("big.abc", b"C" * (request_rules.ABC_BYTES_LIMIT + 1), ui_text.ABC_TOO_LARGE),
        ("binary.abc", b"\xff\xfe\x00\x01binary", ui_text.ABC_NOT_TEXT),
        ("latin.abc", "caf\xe9".encode("latin-1"), ui_text.ABC_NOT_TEXT),
        ("empty.abc", b"  \n", ui_text.ABC_EMPTY),
    ],
)
def test_bad_uploads_are_rejected(tmp_path, name, data, message):
    path = tmp_path / name
    path.write_bytes(data)
    with pytest.raises(AbcFileRejected) as caught:
        request_rules.read_abc_file(path)
    assert str(caught.value) == message
