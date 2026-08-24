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


if __name__ == "__main__":
    unittest.main()
