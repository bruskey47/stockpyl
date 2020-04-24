import unittest

import numpy as np
from scipy.stats import norm
from scipy.stats import poisson
from scipy.stats import lognorm

from pyinv import ss


# Module-level functions.

def print_status(class_name, function_name):
	"""Print status message."""
	print("module : test_ss   class : {:30s} function : {:30s}".format(class_name, function_name))


def set_up_module():
	"""Called once, before anything else in this module."""
	print_status('---', 'set_up_module()')


def tear_down_module():
	"""Called once, after everything else in this module."""
	print_status('---', 'tear_down_module()')


class TestsSCost(unittest.TestCase):
	@classmethod
	def set_up_class(cls):
		"""Called once, before any tests."""
		print_status('TestsSCost', 'set_up_class()')

	@classmethod
	def tear_down_class(cls):
		"""Called once, after all tests, if set_up_class successful."""
		print_status('TestsSCost', 'tear_down_class()')

	def test_example_4_7(self):
		"""Test that s_s_cost() function correctly evaluates cost in Example 4.7.
		"""
		print_status('TestsSCost', 'test_example_4_7()')

		holding_cost = 1
		stockout_cost = 4
		fixed_cost = 5
		demand_mean = 6

		cost = ss.s_s_cost_discrete(4, 10, holding_cost, stockout_cost,
									fixed_cost, True, demand_mean)
		self.assertAlmostEqual(cost, 8.034111561471644)

	def test_fz_instances(self):
		"""Test Zheng and Federgruen (1991) instances.
		"""
		print_status('TestsSCost', 'test_fz_instances()')

		h = 1
		p = 9
		K = 64
		mu = list(range(10, 80, 5)) + [21, 22, 23, 24, 51, 52, 59, 61, 63, 64]
		s = [6, 10, 14, 19, 23, 28, 33, 37, 42, 47, 52, 56, 62, 67, 15, 16, 17, 18, 43, 44, 51, 52, 54, 55]
		S = [40, 49, 62, 56, 66, 77, 87, 97, 108, 118, 129, 75, 81, 86, 65, 68, 52, 54, 110, 112, 126, 131, 73, 74]
		c = [35.022, 42.698, 49.173, 54.262, 57.819, 61.215, 64.512, 67.776, 70.975, 74.149, 77.306, 78.518, 79.037,
			 79.554, 50.406, 51.632, 52.757, 53.518, 71.611, 72.246, 76.679, 77.929, 78.287, 78.402]

		for n in range(1, len(mu), 5):
			cost = ss.s_s_cost_discrete(s[n], S[n], h, p, K, True, mu[n], None, None)
			self.assertAlmostEqual(cost, c[n], places=3)


class TestsSOptimalsS(unittest.TestCase):
	@classmethod
	def set_up_class(cls):
		"""Called once, before any tests."""
		print_status('TestsSOptimalsS', 'set_up_class()')

	@classmethod
	def tear_down_class(cls):
		"""Called once, after all tests, if set_up_class successful."""
		print_status('TestsSOptimalsS', 'tear_down_class()')

	def test_example_4_7(self):
		"""Test that s_s_discrete_exact() function solves Example 4.7.
		"""
		print_status('TestsSOptimalsS', 'test_example_4_7()')

		holding_cost = 1
		stockout_cost = 4
		fixed_cost = 5
		demand_mean = 6

		s, S, g = ss.s_s_discrete_exact(holding_cost, stockout_cost,
									fixed_cost, True, demand_mean)
		self.assertEqual(s, 4)
		self.assertEqual(S, 10)
		self.assertAlmostEqual(g, 8.034111561471644)

	def test_fz_instances(self):
		"""Test Zheng and Federgruen (1991) instances.
		"""
		print_status('TestsSOptimalsS', 'test_fz_instances()')

		h = 1
		p = 9
		K = 64
		mu = list(range(10, 80, 5)) + [21, 22, 23, 24, 51, 52, 59, 61, 63, 64]
		s_opt = [6, 10, 14, 19, 23, 28, 33, 37, 42, 47, 52, 56, 62, 67, 15, 16, 17, 18, 43, 44, 51, 52, 54, 55]
		S_opt = [40, 49, 62, 56, 66, 77, 87, 97, 108, 118, 129, 75, 81, 86, 65, 68, 52, 54, 110, 112, 126, 131, 73, 74]
		c_opt = [35.022, 42.698, 49.173, 54.262, 57.819, 61.215, 64.512, 67.776, 70.975, 74.149, 77.306, 78.518, 79.037,
			 79.554, 50.406, 51.632, 52.757, 53.518, 71.611, 72.246, 76.679, 77.929, 78.287, 78.402]

		for n in range(1, len(mu), 5):
			s, S, g = ss.s_s_discrete_exact(h, p, K, True, mu[n])
			self.assertEqual(s, s_opt[n])
			self.assertEqual(S, S_opt[n])
			self.assertAlmostEqual(g, c_opt[n], places=3)