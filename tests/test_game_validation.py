"""Focused checks for the game-record validation contract."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import validate as validator


class GameValidationTests(unittest.TestCase):
    def _validate_game(self, record: dict[str, object], *, shard: str = "ha") -> list[str]:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            record_path = data_dir / "game" / shard / f"{record['slug']}.json"
            record_path.parent.mkdir(parents=True)
            record_path.write_text(json.dumps(record), encoding="utf-8")
            return validator.validate_games(data_dir)

    def test_accepts_well_formed_game_record(self) -> None:
        errors = self._validate_game(
            {
                "slug": "hades",
                "name": "Hades",
                "verified": True,
                "source_urls": ["https://example.com/hades"],
                "release_date": "2020-09-17",
                "rating": 4.8,
                "rating_count": 1000,
                "metacritic": 93,
                "playtime_hours": 25,
                "platforms": ["PC", "Nintendo Switch"],
                "genres": ["Action"],
                "developers": ["Supergiant Games"],
                "esrb_rating": "Teen",
                "background_image": "https://example.com/hades.jpg",
            }
        )
        self.assertEqual(errors, [])

    def test_rejects_invalid_game_metadata(self) -> None:
        errors = self._validate_game(
            {
                "slug": "hades",
                "name": " ",
                "verified": "yes",
                "source_urls": ["https://example.com/hades"],
                "platforms": ["PC", 4],
                "rating_count": -1,
                "playtime_hours": -1,
                "esrb_rating": "Unknown",
                "background_image": "file:///tmp/hades.jpg",
            }
        )
        self.assertTrue(any("name must be a non-empty string" in error for error in errors))
        self.assertTrue(any("verified must be a boolean" in error for error in errors))
        self.assertTrue(any("platforms must be a list of non-empty strings" in error for error in errors))
        self.assertTrue(any("rating_count=-1 out of range" in error for error in errors))
        self.assertTrue(any("playtime_hours=-1 out of range" in error for error in errors))
        self.assertTrue(any("esrb_rating 'Unknown'" in error for error in errors))
        self.assertTrue(any("background_image must be an http(s) URL" in error for error in errors))

    def test_rejects_game_outside_slug_shard(self) -> None:
        errors = self._validate_game(
            {
                "slug": "hades",
                "name": "Hades",
                "verified": False,
                "source_urls": ["https://example.com/hades"],
            },
            shard="ga",
        )
        self.assertTrue(any("belongs in 'ha'" in error for error in errors))

    def test_default_validation_streams_games_instead_of_loading_them(self) -> None:
        loaded_categories: list[str] = []

        def load_without_games(category: str):
            loaded_categories.append(category)
            self.assertNotEqual(category, "game")
            return []

        with (
            mock.patch.object(validator, "_load", side_effect=load_without_games),
            mock.patch.object(validator, "validate_games", return_value=[] ) as streamed_games,
        ):
            self.assertEqual(validator.validate(), [])

        self.assertNotIn("game", loaded_categories)
        streamed_games.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
