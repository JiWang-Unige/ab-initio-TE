import unittest
import numpy as np

from diagnose_worm_generalization import ranking_diagnostics


class RankingTest(unittest.TestCase):
    def test_prevalence_standardization_removes_negative_replication(self):
        score = np.array([3., 2., 1., 0.])
        truth = np.array([1., 0., 1., 0.])
        base = ranking_diagnostics(score, truth, .25)
        replicated = ranking_diagnostics(np.array([3., 2., 2., 1., 0., 0.]), np.array([1., 0., 0., 1., 0., 0.]), .25)
        self.assertAlmostEqual(base["ap_at_cal_prevalence"], replicated["ap_at_cal_prevalence"])
        self.assertAlmostEqual(base["label_oracle_threshold_f1"], .8)


if __name__ == "__main__":
    unittest.main()
