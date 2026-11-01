import unittest
import numpy as np

from rag.answering import create_prompt
from rag.documents import Chunk
from rag.retrieval import build_index, search


class FakeEncoder:
    def encode(self, texts, **_kwargs):
        vectors = []
        for text in texts:
            t = text.lower()
            vectors.append([float("cat" in t), float("robot" in t)])
        return np.array(vectors, dtype=np.float32)


class TestRetrieval(unittest.TestCase):
    def test_vector_search_returns_relevant_passage_with_page(self):
        chunks = [
            Chunk("pets.pdf", 4, "The cat is resting.", "pets:4:1"),
            Chunk("tech.pdf", 7, "The robot is autonomous.", "tech:7:1"),
        ]
        encoder = FakeEncoder()
        index = build_index(chunks, encoder)
        hits = search(index, "Explain robot", encoder, top_k=1)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].chunk.doc_name, "tech.pdf")
        self.assertEqual(hits[0].chunk.page, 7)
        self.assertGreater(hits[0].score, 0.99)

    def test_prompt_includes_only_retrieved_source_labels(self):
        chunk = Chunk("notes.pdf", 3, "Evaluation uses grounded citations.", "notes:3:1")
        hits = search(build_index([chunk], FakeEncoder()), "evaluation", FakeEncoder())
        prompt = create_prompt("How are answers evaluated?", hits)
        self.assertIn('id="1"', prompt)
        self.assertIn('document="notes.pdf"', prompt)
        self.assertIn('page="3"', prompt)
        self.assertIn("Evaluation uses grounded citations.", prompt)
        self.assertIn("How are answers evaluated?", prompt)

    def test_blank_search_has_no_results(self):
        chunk = Chunk("notes.pdf", 3, "The robot moves.", "notes:3:1")
        index = build_index([chunk], FakeEncoder())
        self.assertEqual(search(index, "  ", FakeEncoder()), [])


if __name__ == "__main__":
    unittest.main()
