from __future__ import annotations

import pytest

from newsr.tts.normalize import normalize_english


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Apple raised the price by $300 in 2026.", "Apple raised the price by three hundred dollars in twenty twenty-six."),
        ("Etched raised $700M at a $21.5bn valuation.", "Etched raised seven hundred million dollars at a twenty-one point five billion dollars valuation."),
        ("a 50% jump on Oct 5th at 10:30", "a fifty percent jump on Oct fifth at ten thirty"),
        ("the 1990s and 1,250 people", "the nineteen nineties and one thousand, two hundred and fifty people"),
        ("Pixel 10a with 8 GB and 5000mAh", "Pixel ten a with eight gigabytes and five thousand milliamp hours"),
        ("TSMC, AWS and NASA watched the M5 Pro", "tee-ess-em-see, ay-double-you-ess and nasa watched the em five Pro"),
        ("GPUs & CPUs — fast", "gee-pee-yous and see-pee-yous , fast"),
    ],
)
def test_normalize_english_writes_numbers_units_and_acronyms_as_words(text: str, expected: str) -> None:
    assert normalize_english(text) == expected
