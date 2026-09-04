import itertools
import unittest

from diagnose_token_ceiling import optimal_f1, token_masses


class TokenCeilingTest(unittest.TestCase):
    def test_ceiling_matches_exhaustive_token_assignments(self):
        masses = [(4, 2, 6), (2, 3, 6), (1, 0, 1), (0, 0, 6)]
        total_positive = sum(p for p, _, _ in masses)
        brute = 0
        for mask in itertools.product((0, 1), repeat=len(masses)):
            tp = sum(p * selected for (p, _, _), selected in zip(masses, mask))
            fp = sum(n * selected for (_, n, _), selected in zip(masses, mask))
            brute = max(brute, 2 * tp / (total_positive + tp + fp))
        self.assertAlmostEqual(optimal_f1(masses)[0], brute)

    def test_unknown_hard_negative_and_single_base_tail(self):
        self.assertEqual(token_masses("11H0??1?"), [(2, 2, 6), (1, 0, 1), (0, 0, 1)])


if __name__ == "__main__":
    unittest.main()
