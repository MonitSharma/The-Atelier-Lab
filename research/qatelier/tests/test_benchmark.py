from __future__ import annotations

import unittest

import numpy as np

from research.qatelier.benchmark import (
    SUPPORTED_FAMILIES,
    BenchmarkDataset,
    InteractionProblem,
    generate_interaction_order_data,
    make_interaction_problem,
)


class BenchmarkProblemTests(unittest.TestCase):
    def test_same_problem_and_split_seed_reproduce_exactly(self) -> None:
        first_problem = make_interaction_problem(
            n_features=6, order=3, family="rotated", problem_seed=17
        )
        second_problem = make_interaction_problem(
            n_features=6, order=3, family="rotated", problem_seed=17
        )
        first = first_problem.sample(n=80, seed=23)
        second = second_problem.sample(n=80, seed=23)

        self.assertIsInstance(first_problem, InteractionProblem)
        self.assertEqual(first_problem.target_fingerprint, second_problem.target_fingerprint)
        np.testing.assert_array_equal(first_problem.rotation, second_problem.rotation)
        np.testing.assert_array_equal(first.features, second.features)
        np.testing.assert_array_equal(first.labels, second.labels)
        self.assertEqual(first.metadata, second.metadata)

    def test_problem_construction_and_sampling_do_not_consume_global_rng(self) -> None:
        np.random.seed(1234)
        expected = np.random.random(5)

        np.random.seed(1234)
        problem = make_interaction_problem(
            n_features=5, order=2, family="misaligned", problem_seed=9
        )
        problem.sample(n=24, seed=10)
        observed = np.random.random(5)

        np.testing.assert_array_equal(observed, expected)

    def test_supported_families_have_expected_shapes_and_binary_labels(self) -> None:
        for family in SUPPORTED_FAMILIES:
            with self.subTest(family=family):
                problem = make_interaction_problem(
                    n_features=7, order=3, family=family, problem_seed=4
                )
                data = problem.sample(n=31, seed=5)
                self.assertIsInstance(data, BenchmarkDataset)
                self.assertEqual(data.features.shape, (31, 7))
                self.assertEqual(data.labels.shape, (31,))
                self.assertEqual(data.features.dtype, np.float64)
                self.assertTrue(set(np.unique(data.labels)).issubset({0, 1}))
                self.assertEqual(data.metadata["family"], family)
                self.assertEqual(data.metadata["target_fingerprint"], problem.target_fingerprint)

    def test_trigonometric_alias_is_fourier(self) -> None:
        problem = make_interaction_problem(
            n_features=5, order=2, family="trigonometric", problem_seed=11
        )
        data = problem.sample(n=20, seed=12)
        self.assertEqual(problem.family, "fourier")
        self.assertEqual(data.metadata["family"], "fourier")
        self.assertEqual(data.metadata["interaction_order"], 2)
        self.assertEqual(data.metadata["target_definition"]["fourier_frequencies"], (1, 1))

    def test_split_sampling_reuses_target_and_threshold_without_reusing_rows(self) -> None:
        problem = make_interaction_problem(
            n_features=8, order=4, family="rotated", problem_seed=31
        )
        train = problem.sample(n=128, seed=101)
        validation = problem.sample(n=96, seed=102)
        test = problem.sample(n=96, seed=103)

        splits = (train, validation, test)
        fingerprints = {split.metadata["target_fingerprint"] for split in splits}
        thresholds = {split.metadata["threshold"] for split in splits}
        sample_fingerprints = {split.metadata["sample_fingerprint"] for split in splits}

        self.assertEqual(fingerprints, {problem.target_fingerprint})
        self.assertEqual(thresholds, {0.0})
        self.assertEqual(len(sample_fingerprints), len(splits))
        self.assertEqual({split.metadata["problem_seed"] for split in splits}, {31})
        self.assertEqual(
            {split.metadata["sample_seed"] for split in splits}, {101, 102, 103}
        )
        self.assertEqual(problem.threshold_source, "natural_zero_for_symmetric_target")

        for split in splits:
            expected_labels = (problem.score(split.features) >= problem.threshold).astype(np.int8)
            np.testing.assert_array_equal(split.labels, expected_labels)

    def test_threshold_is_not_recalibrated_from_each_sample(self) -> None:
        problem = make_interaction_problem(
            n_features=8, order=4, family="polynomial", problem_seed=2
        )
        first = problem.sample(n=100, seed=2)
        second = problem.sample(n=101, seed=3)

        self.assertEqual(first.metadata["threshold"], problem.threshold)
        self.assertEqual(second.metadata["threshold"], problem.threshold)
        self.assertEqual(first.metadata["threshold_source"], "natural_zero_for_symmetric_target")
        self.assertEqual(second.metadata["threshold_source"], "natural_zero_for_symmetric_target")
        # A fixed zero boundary is allowed to produce unequal class counts;
        # exact balancing must not be imposed separately on each split.
        self.assertNotEqual(first.metadata["class_counts"], {"0": 50, "1": 50})

    def test_rotated_and_misaligned_target_parameters_are_shared_across_splits(self) -> None:
        for family, attribute in (("rotated", "rotation"), ("misaligned", "directions")):
            with self.subTest(family=family):
                problem = make_interaction_problem(
                    n_features=6, order=3, family=family, problem_seed=41
                )
                repeat = make_interaction_problem(
                    n_features=6, order=3, family=family, problem_seed=41
                )
                self.assertEqual(problem.target_fingerprint, repeat.target_fingerprint)
                np.testing.assert_array_equal(getattr(problem, attribute), getattr(repeat, attribute))

                left = problem.sample(n=32, seed=1)
                right = problem.sample(n=32, seed=2)
                self.assertEqual(
                    left.metadata["target_fingerprint"], right.metadata["target_fingerprint"]
                )
                self.assertNotEqual(
                    left.metadata["sample_fingerprint"], right.metadata["sample_fingerprint"]
                )

    def test_fourier_target_parameters_are_fixed_by_problem_seed(self) -> None:
        problem = make_interaction_problem(
            n_features=8, order=4, family="fourier", problem_seed=7
        )
        repeat = make_interaction_problem(
            n_features=8, order=4, family="fourier", problem_seed=7
        )
        self.assertEqual(problem.target_fingerprint, repeat.target_fingerprint)
        np.testing.assert_array_equal(problem.fourier_frequencies, repeat.fourier_frequencies)
        self.assertEqual(problem.sample(40, 4).metadata["threshold"], 0.0)

    def test_noise_is_sampling_only_and_reproducible(self) -> None:
        clean_problem = make_interaction_problem(
            n_features=5, order=2, family="aligned", problem_seed=13
        )
        noisy_problem = make_interaction_problem(
            n_features=5,
            order=2,
            family="aligned",
            problem_seed=13,
            observation_noise_std=0.25,
            label_noise=0.2,
        )
        clean = clean_problem.sample(n=200, seed=3)
        noisy = noisy_problem.sample(n=200, seed=3)
        noisy_repeat = noisy_problem.sample(n=200, seed=3)

        self.assertEqual(clean_problem.target_fingerprint, noisy_problem.target_fingerprint)
        self.assertFalse(np.array_equal(clean.features, noisy.features))
        np.testing.assert_array_equal(noisy.features, noisy_repeat.features)
        np.testing.assert_array_equal(noisy.labels, noisy_repeat.labels)
        self.assertEqual(
            noisy.metadata["noise"],
            {"observation_std": 0.25, "label_flip_probability": 0.2},
        )

    def test_diagnostics_are_empirical_and_do_not_define_the_threshold(self) -> None:
        problem = make_interaction_problem(
            n_features=6, order=3, family="fourier", problem_seed=5
        )
        data = problem.sample(n=64, seed=6)
        diagnostics = data.metadata["diagnostics"]

        self.assertEqual(diagnostics["analytical"]["interaction_order"], 3)
        self.assertEqual(diagnostics["analytical"]["threshold"], 0.0)
        self.assertEqual(diagnostics["empirical"]["n_samples"], 64)
        self.assertIn("score_std", diagnostics["empirical"])
        self.assertIn("near_threshold_fraction", diagnostics["empirical"])
        self.assertEqual(diagnostics["empirical"]["class_counts"], data.metadata["class_counts"])

    def test_invalid_or_conflicting_problem_arguments_are_rejected(self) -> None:
        with self.assertRaises(TypeError):
            make_interaction_problem(n_features=4)  # type: ignore[call-arg]
        with self.assertRaises(ValueError):
            make_interaction_problem(n_features=4, order=2, interaction_order=3)
        with self.assertRaises(ValueError):
            make_interaction_problem(n_features=4, order=2, label_noise=1.1)
        with self.assertRaises(ValueError):
            make_interaction_problem(n_features=4, order=2, threshold=float("nan"))


class LegacyBenchmarkWrapperTests(unittest.TestCase):
    def test_legacy_wrapper_remains_deterministic(self) -> None:
        first = generate_interaction_order_data(80, 6, 3, family="rotated", seed=17)
        second = generate_interaction_order_data(80, 6, 3, family="rotated", seed=17)

        np.testing.assert_array_equal(first.features, second.features)
        np.testing.assert_array_equal(first.labels, second.labels)
        self.assertEqual(first.metadata, second.metadata)
        self.assertEqual(first.metadata["seed"], 17)
        self.assertEqual(first.metadata["sample_seed"], 17)


if __name__ == "__main__":
    unittest.main()
