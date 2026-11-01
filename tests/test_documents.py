import unittest
import pymupdf as fitz

from rag.documents import chunk_text, clean_text, read_pdf


class TestDocuments(unittest.TestCase):
    def test_clean_text_joins_wrapped_words(self):
        self.assertEqual(clean_text("Docu-\nment   retrieval\nworks"), "Document retrieval works")

    def test_chunk_text_overlapping_and_bounded(self):
        text = " ".join([f"word{i}" for i in range(100)])
        parts = chunk_text(text, chunk_size=100, overlap=20)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(len(p) <= 100 for p in parts))
        self.assertIn("word0", parts[0])
        self.assertIn("word99", parts[-1])

    def test_chunk_text_empty_and_parameter_validation(self):
        self.assertEqual(chunk_text("    "), [])
        with self.assertRaises(ValueError):
            chunk_text("hello", chunk_size=100, overlap=100)

    def test_read_pdf_retains_page_references(self):
        pdf = fitz.open()
        for content in ("Embeddings encode text as vectors.", "Retrieval selects the most similar chunks."):
            page = pdf.new_page()
            page.insert_text((72, 72), content)
        data = pdf.tobytes()
        pdf.close()

        chunks, n_pages = read_pdf(data, "guide.pdf")
        self.assertEqual(n_pages, 2)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].page, 1)
        self.assertEqual(chunks[1].page, 2)
        self.assertEqual(chunks[1].doc_name, "guide.pdf")
        self.assertIn("Retrieval", chunks[1].text)

    def test_invalid_pdf_rejected(self):
        with self.assertRaises(ValueError):
            read_pdf(b"not pdf data", "fake.pdf")


if __name__ == "__main__":
    unittest.main()
