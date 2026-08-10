from __future__ import annotations

import unittest

import numpy as np

from research.qatelier.benchmark import (
    SUPPORTED_FAMILIES,
    BenchmarkDataset,
    generate_interaction_order_data,
)


class BenchmarkGeneratorTests(unittest.TestCase):
    def test_same_seed_reproduces_arrays_and_metadata(self) -> None:
        first = generate_interaction_order_data(
            80, 6, 3, family="rotated", seed=17
        )
        second = generate_interaction_order_data(
            80, 6, 3, family="rotated", seed=17
        )

        np.testing.assert_array_equal(first.features, second.features)
        np.testing.assert_array_equal(first.labels, second.labels)
        self.assertEqual(first.metadata, second.metadata)

    def test_global_numpy_random_state_is_not_consumed(self) -> None:
        np.random.seed(1234)
        expected = np.random.random(5)
        np.random.seed(1234)
        generate_interaction_order_data(24, 5, 2, seed=9)
        observed = np.random.random(5)
        np.testing.assert_array_equal(observed, expected)

    def test_all_families_have_expected_shape_and_binary_labels(self) -> None:
        for family in SUPPORTED_FAMILIES:
            with self.subTest(family=family):
                data = generate_interaction_order_data(31, 7, 3, family=family, seed=4)
                self.assertIsInstance(data, BenchmarkDataset)
                self.assertEqual(data.features.shape, (31, 7))
                self.assertEqual(data.labels.shape, (31,))
                self.assertEqual(data.features.dtype, np.float64)
                self.assertTrue(set(np.unique(data.labels)).issubset({0, 1}))

    def test_even_sample_count_is_exactly_balanced(self) -> None:
        data = generate_interaction_order_data(100, 8, 4, family="polynomial", seed=2)
        counts = np.bincount(data.labels, minlength=2)
        np.testing.assert_array_equal(counts, np.array([50, 50]))
        self.assertEqual(data.metadata["class_counts"], {"0": 50, "1": 50})

    def test_interaction_order_metadata_is_preserved(self) -> None:
        data = generate_interaction_order_data(
            20, 5, 2, family="trigonometric", seed=11
        )
        self.assertEqual(data.metadata["family"], "fourier")
        self.assertEqual(data.metadata["interaction_order"], 2)
        self.assertEqual(data.metadata["n_samples"], 20)
        self.assertEqual(data.metadata["n_features"], 5)
        self.assertEqual(data.metadata["seed"], 11)
        self.assertEqual(data.metadata["interaction_coordinates"], (0, 1))


if __name__ == "__main__":
    unittest.main()
