import unittest
from pathlib import Path
from voice_assistant import _words_to_number, describe_position, _ordinal_it, WHISPER_LANGUAGE
from composition_controller import RETURN_PARTS_MESSAGE
from parts_catalog import PARTS_CATALOG, build_catalog_text


class EnglishLanguageTests(unittest.TestCase):
    def test_english_transcription_language(self):
        self.assertEqual(WHISPER_LANGUAGE, "en")

    def test_spoken_digits(self):
        for text, expected in [("six three two", "632"), ("C six five eight", "658"), ("A zero zero three", "003")]:
            with self.subTest(text=text):
                self.assertEqual(_words_to_number(text), expected)

    def test_compound_numbers(self):
        for text, expected in [("six hundred thirty two", "632"), ("eight hundred and twenty-three", "823"), ("fifty four", "54")]:
            with self.subTest(text=text):
                self.assertEqual(_words_to_number(text), expected)

    def test_empty_number_input(self):
        self.assertEqual(_words_to_number("red nut"), "")

    def test_english_position_sentence(self):
        text = describe_position((0.12, -0.05, 0.58))
        self.assertIn("12 centimetres to the right", text)
        self.assertIn("5 centimetres", text)
        self.assertIn("58 centimetres", text)

    def test_english_return_warning(self):
        self.assertEqual(RETURN_PARTS_MESSAGE, "RETURN THE PARTS TO THE STARTING AREA")

    def test_catalogue_text_in_english(self):
        text = build_catalog_text({"C658"})
        self.assertIn("C658", text)
        self.assertIn("red nut", text.lower())
        self.assertEqual(set(PARTS_CATALOG), {"A003","A004","A045","A046","A050","A051","A053","A054","A057","A077","A132","A306","A545","A622","A632","B577","B823","C658"})

    def test_english_ordinals(self):
        self.assertEqual(_ordinal_it(1), "first")
        self.assertEqual(_ordinal_it(10), "tenth")

    def test_english_tts_selection(self):
        source = Path(__import__("voice_assistant").__file__).read_text()
        self.assertIn('("english", "en_", "en-")', source)


if __name__ == "__main__":
    unittest.main()
