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
