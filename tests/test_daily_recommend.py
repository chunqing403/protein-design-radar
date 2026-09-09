import datetime as dt
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "daily_recommend.py"
SPEC = importlib.util.spec_from_file_location("daily_recommend", SCRIPT)
daily_recommend = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = daily_recommend
SPEC.loader.exec_module(daily_recommend)


class CrossrefPrefixQueryTests(unittest.TestCase):
    def test_paginates_and_maps_crossref_records(self):
        pages = [
            {
                "message": {
                    "items": [
                        {
                            "DOI": "10.1038/example-1",
                            "title": ["AI-enabled protein design"],
                            "container-title": ["Nature Biotechnology"],
                            "author": [{"given": "Ada", "family": "Lovelace"}],
                            "created": {"date-parts": [[2026, 8, 23]]},
                            "URL": "https://doi.org/10.1038/example-1",
                        }
                    ],
                    "next-cursor": "page-2",
                }
            },
            {
                "message": {
                    "items": [
                        {
                            "DOI": "10.1038/example-2",
                            "title": ["Deep learning for enzyme design"],
                            "container-title": ["Nature Methods"],
                            "created": {"date-parts": [[2026, 8, 24]]},
                            "URL": "https://doi.org/10.1038/example-2",
                        }
                    ],
                    "next-cursor": "page-3",
                }
            },
        ]

        def fake_request(url):
            self.assertIn("prefix%3A10.1038", url)
            self.assertIn("from-created-date%3A2026-08-22", url)
            self.assertIn("until-created-date%3A2026-08-24", url)
            return json.dumps(pages.pop(0))

        scans = [{"name": "Nature Portfolio", "prefix": "10.1038", "max_results": 2, "page_size": 1}]
        with patch.object(daily_recommend, "request_text", side_effect=fake_request):
            papers = daily_recommend.crossref_prefix_query(
                scans,
                dt.date(2026, 8, 22),
                dt.date(2026, 8, 24),
                10,
            )

        self.assertEqual([paper.doi for paper in papers], ["10.1038/example-1", "10.1038/example-2"])
        self.assertEqual(papers[0].source, "Nature Biotechnology")
        self.assertEqual(papers[0].authors, ["Ada Lovelace"])

    def test_uses_issn_filter_for_individual_journal_scan(self):
        payload = {
            "message": {
                "items": [
                    {
                        "DOI": "10.1093/bioinformatics/example",
                        "title": ["Machine learning for protein design"],
                        "container-title": ["Bioinformatics"],
                        "created": {"date-parts": [[2026, 8, 24]]},
                    }
                ],
                "next-cursor": "done",
            }
        }

        def fake_request(url):
            self.assertIn("issn%3A1367-4811", url)
            return json.dumps(payload)

        scans = [{"name": "Bioinformatics", "issn": "1367-4811", "max_results": 10}]
        with patch.object(daily_recommend, "request_text", side_effect=fake_request):
            papers = daily_recommend.crossref_issn_query(
                scans,
                dt.date(2026, 8, 22),
                dt.date(2026, 8, 24),
                10,
            )

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].source, "Bioinformatics")


class PreprintQueryTests(unittest.TestCase):
    def test_uses_api_page_count_to_advance_cursor(self):
        pages = {
            "/0": {
                "messages": [{"count": 2, "total": "3"}],
                "collection": [
                    {
                        "doi": "10.1101/example-1",
                        "title": "First protein design paper",
                        "authors": "Ada Lovelace",
                        "abstract": "Protein design.",
                        "date": "2026-09-07",
                    },
                    {
                        "doi": "10.1101/example-2",
                        "title": "Second protein design paper",
                        "authors": "Grace Hopper",
                        "abstract": "Protein design.",
                        "date": "2026-09-07",
                    },
                ],
            },
            "/2": {
                "messages": [{"count": 1, "total": "3"}],
                "collection": [
                    {
                        "doi": "10.1101/example-3",
                        "title": "Third protein design paper",
                        "authors": "Katherine Johnson",
                        "abstract": "Protein design.",
                        "date": "2026-09-08",
                    }
                ],
            },
        }

        def fake_request(url, **kwargs):
            page = next(payload for suffix, payload in pages.items() if url.endswith(suffix))
            return json.dumps(page)

        with patch.object(daily_recommend, "request_text", side_effect=fake_request) as request:
            papers = daily_recommend.preprint_query(
                "biorxiv",
                dt.date(2026, 9, 7),
                dt.date(2026, 9, 8),
                10,
            )

        self.assertEqual(request.call_count, 2)
        self.assertEqual([paper.doi for paper in papers], [
            "10.1101/example-1",
            "10.1101/example-2",
            "10.1101/example-3",
        ])
        self.assertTrue(all(paper.source == "bioRxiv" for paper in papers))


class ScoreFilterRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = daily_recommend.load_json(
            SCRIPT.parents[1] / "config" / "topics.json", {}
        )

    def test_watchlisted_rfoptimization_paper_is_retained(self):
        paper = daily_recommend.Paper(
            title="RFOptimization: Guiding Design Optimization with All-Atom Structure Prediction",
            authors=[],
            abstract="A framework for biomolecular binder optimization and protein design.",
            source="bioRxiv",
            published="2026-09-07",
            url="https://doi.org/10.64898/2026.09.04.749184",
            doi="10.64898/2026.09.04.749184",
        )

        scored = daily_recommend.score_paper(paper, self.config)

        self.assertGreaterEqual(scored.score, self.config["min_score"])
        self.assertNotEqual(scored.topics, ["Filtered"])

    def test_rna_structure_prediction_title_does_not_bypass_domain_filter(self):
        paper = daily_recommend.Paper(
            title="Agent-driven Model Development for RNA 3D Structure Prediction",
            authors=[],
            abstract="The method borrows ideas from protein folding benchmarks.",
            source="bioRxiv",
            published="2026-09-08",
            url="https://example.org/rna-model",
        )

        scored = daily_recommend.score_paper(paper, self.config)

        self.assertEqual(scored.score, -996)
        self.assertEqual(scored.reasons, ["missing protein/biomolecular term in title"])


class ReadmeCategoryTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "paper_category_order": [
                "Structure generation",
                "Sequence design",
                "Binders and therapeutics",
                "General",
            ],
            "paper_category_labels": {
                "Structure generation": "Structure Generation / 结构生成",
                "Sequence design": "Sequence Design / 序列设计",
                "Binders and therapeutics": "Binders & Therapeutics / 结合蛋白与治疗",
                "General": "General / 综合",
            },
            "topic_profiles": {
                "Structure generation": [],
                "Sequence design": [],
                "Binders and therapeutics": [],
            },
        }

    @staticmethod
    def paper(title, source_id, topics, score):
        return daily_recommend.Paper(
            title=title,
            authors=["Ada Lovelace"],
            abstract="",
            source="Test Journal",
            published="2026-09-01",
            url=f"https://example.org/{source_id}",
            source_id=source_id,
            score=score,
            topics=topics,
        )

    def test_uses_first_known_topic_as_unique_primary_category(self):
        paper = self.paper(
            "A multi-topic paper",
            "multi-topic",
            ["Unknown", "Sequence design", "Binders and therapeutics"],
            10,
        )

        self.assertEqual(
            daily_recommend.primary_paper_category(paper, self.config),
            "Sequence design",
        )

    def test_readme_renders_directory_counts_and_each_library_paper_once(self):
        structure = self.paper(
            "Structure paper",
            "structure",
            ["Structure generation", "Sequence design"],
            12,
        )
        binder = self.paper(
            "Binder paper",
            "binder",
            ["Binders and therapeutics"],
            9,
        )
        library = {
            "papers": {
                structure.key: daily_recommend.paper_to_record(structure, "2026-08-30"),
                binder.key: daily_recommend.paper_to_record(binder, "2026-09-01"),
            }
        }

        section = daily_recommend.render_readme_section(
            dt.date(2026, 9, 2), [], self.config, library
        )
        categorized_library = section.split(
            "### Categorized Paper Library / 分类文献库", 1
        )[1]

        self.assertIn(
            "| [Structure Generation / 结构生成](#paper-category-structure-generation) | 1 |",
            section,
        )
        self.assertIn(
            "| [Binders & Therapeutics / 结合蛋白与治疗](#paper-category-binders-and-therapeutics) | 1 |",
            section,
        )
        self.assertEqual(categorized_library.count("Structure paper"), 1)
        self.assertEqual(categorized_library.count("Binder paper"), 1)
        self.assertIn("first seen 2026-08-30", categorized_library)


if __name__ == "__main__":
    unittest.main()
