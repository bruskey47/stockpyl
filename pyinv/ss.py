# ===============================================================================
# PyInv - ss Module
# -------------------------------------------------------------------------------
# Version: 0.0.0
# Updated: 04-15-2020
# Author: Larry Snyder
# License: GPLv3
# ===============================================================================

"""The :mod:`ss` module contains code for solving the :math:`(s,S)` problem.

Functions in this module are called directly; they are not wrapped in a class.

The notation and references (equations, sections, examples, etc.) used below
refer to Snyder and Shen, *Fundamentals of Supply Chain Theory*, 2nd edition
(2019).

"""

from scipy import integrate
from scipy.stats import norm
from scipy.stats import poisson
from scipy.optimize import fsolve

from pyinv.newsvendor import *
from pyinv.eoq import *
#import pyinv.loss_functions as lf


def s_s_cost_discrete(reorder_point, order_up_to_level, holding_cost,
					  stockout_cost, fixed_cost, use_poisson, demand_mean=None,
					  demand_hi=None, demand_pmf=None):
	"""Calculate the exact cost of the given solution for an :math:`(s,S)`
	policy with given parameters under a discrete (Poisson or custom) demand
	distribution.

	Uses method described in Zheng and Federgruen (1991).

	Parameters
	----------
	reorder_point : float
		Reorder point. [:math:`s`]
	order_up_to_level : float
		Order-up-to level. [:math:`S`]
	holding_cost : float
		Holding cost per item per period. [:math:`h`]
	stockout_cost : float
		Stockout cost per item per period. [:math:`p`]
	fixed_cost : float
		Fixed cost per order. [:math:`K`]
	poisson_dist : bool
		Set to ``True`` to use Poisson distribution, ``False`` to use custom
		discrete distribution. If ``True``, then ``demand_mean`` must be
		provided; if ``False``, then ``demand_hi`` and ``demand_pdf`` must
		be provied.
	demand_mean : float, optional
		Mean demand per period. Required if ``use_poisson`` is ``True``,
		ignored otherwise. [:math:`\\mu`]
	demand_hi : int, optional
		Upper limit of support of demand per period (lower limit is assumed to
		be 0). Required if ``use_poisson`` is ``False``, ignored otherwise.
	demand_pmf : list, optional
		List of pmf values for demand values 0, ..., ``demand_hi``. Required
		if ``use_poisson`` is ``False``, ignored otherwise.

	Returns
	-------
	cost : float
		Expected cost per period. [:math:`g(s,S)`]


	**Equations Used** (equation (5.7)):

	.. math::

		g(s,S) = \\frac{K + \\sum_{d=0}^{S-s-1} m(d)g(S-d)}{M(S-s)},

	where :math:`g(\cdot)` is the newsvendor cost function and :math:`M(\\cdot)`
	and :math:`m(\\cdot)` are as described in equations (4.71)--(4.75).

	**Example** (Example 4.7):

	.. testsetup:: *

		from pyinv.ss import *

	.. doctest::

		>>> s_s_cost_discrete(4, 10, 1, 4, 5, True, 6)
		8.03645143944724

	"""

	# TODO: improve performance

	# Check parameters.
	assert is_integer(reorder_point), "reorder_point must be an integer"
	assert is_integer(order_up_to_level), "order_up_to_level must be an integer"
	assert holding_cost > 0, "holding_cost must be positive."
	assert stockout_cost > 0, "stockout_cost must be positive."
	assert fixed_cost > 0, "fixed_cost must be positive."
	assert demand_mean is None or demand_mean >= 0, "demand_mean must be non-negative (or None)"
	assert demand_hi is None or (demand_hi >= 0 and is_integer(demand_hi)), \
		"demand_hi must be a non-negative integer (or None)"
	assert demand_pmf is None or \
		(is_list(demand_pmf) and len(demand_pmf) == demand_hi+1), \
		"demand_pmf must be a list of length demand_hi+1 (or None)"

	# Determine demand pmf to use based on use_poisson.
	if use_poisson:
		# We only need values up through S-s.
		pmf = poisson.pmf(range(int(order_up_to_level) - int(reorder_point)), demand_mean)
	else:
		pmf = demand_pmf

	# Calculate m(.) function.
	m = np.zeros(int(order_up_to_level) - int(reorder_point))
	m[0] = 1.0 / (1 - pmf[0])
	for j in range(1, int(order_up_to_level) - int(reorder_point)):
		m[j] = m[0] * np.sum([pmf[l] * m[j-l] for l in range(1, j+1)])
		# old (incorrect) method:
		# m[j] = np.sum([pmf[d] * m[j-d] for d in range(j+1)])

	# Calculate M(.) function.
	M = np.zeros(int(order_up_to_level) - int(reorder_point) + 1)
	M[0] = 0
	for j in range(1, int(order_up_to_level) - int(reorder_point) + 1):
		M[j] = M[j-1] + m[j-1]

	# Calculate g(s,S).
	cost = fixed_cost
	for d in range(int(order_up_to_level) - int(reorder_point)):
		if use_poisson:
			cost += m[d] * newsvendor_poisson_cost(order_up_to_level - d,
				holding_cost=holding_cost,
				stockout_cost=stockout_cost,
				demand_mean=demand_mean)
		else:
			cost += m[d] * newsvendor_discrete(
				holding_cost=holding_cost,
				stockout_cost=stockout_cost,
				demand_distrib=None,
				demand_pmf={n: demand_pmf[n] for n in range(demand_hi)},
				base_stock_level=order_up_to_level - d)[1]
	cost /= M[int(order_up_to_level)-int(reorder_point)]

	return cost


def s_s_discrete_exact(holding_cost, stockout_cost, fixed_cost, use_poisson,
					   demand_mean=None, demand_hi=None, demand_pmf=None):
	"""Determine optimal :math:`s` and :math:`S` for an :math:`(s,S)`
	policy under a discrete (Poisson or custom) demand distribution.

	Uses method described in Zheng and Federgruen (1991).

	Parameters
	----------
	holding_cost : float
		Holding cost per item per period. [:math:`h`]
	stockout_cost : float
		Stockout cost per item per period. [:math:`p`]
	fixed_cost : float
		Fixed cost per order. [:math:`K`]
	poisson_dist : bool
		Set to ``True`` to use Poisson distribution, ``False`` to use custom
		discrete distribution. If ``True``, then ``demand_mean`` must be
		provided; if ``False``, then ``demand_hi`` and ``demand_pdf`` must
		be provied.
	demand_mean : float, optional
		Mean demand per period. Required if ``use_poisson`` is ``True``,
		ignored otherwise. [:math:`\\mu`]
	demand_hi : int, optional
		Upper limit of support of demand per period (lower limit is assumed to
		be 0). Required if ``use_poisson`` is ``False``, ignored otherwise.
	demand_pmf : list, optional
		List of pmf values for demand values 0, ..., ``demand_hi``. Required
		if ``use_poisson`` is ``False``, ignored otherwise.

	Returns
	-------
	reorder_point : float
		Reorder point. [:math:`s`]
	order_up_to_level : float
		Order-up-to level. [:math:`S`]
	cost : float
		Expected cost per period. [:math:`g(s,S)`]


	**Algorithm Used:** Exact algorithm for periodic-review :math:`(s,S)`
	policies with discrete demand distribution (Algorithm 4.2)

# TODO

	**Example** (Example 4.7):

	.. testsetup:: *

		from pyinv.ss import *

	.. doctest::

		>>> s_s_cost_discrete(4, 10, 1, 4, 5, True, 6)
		8.03645143944724

	"""

	# TODO: improve performance

	# Check parameters.
	assert holding_cost > 0, "holding_cost must be positive."
	assert stockout_cost > 0, "stockout_cost must be positive."
	assert fixed_cost > 0, "fixed_cost must be positive."
	assert demand_mean is None or demand_mean >= 0, "demand_mean must be non-negative (or None)"
	assert demand_hi is None or (demand_hi >= 0 and is_integer(demand_hi)), \
		"demand_hi must be a non-negative integer (or None)"
	assert demand_pmf is None or \
		(is_list(demand_pmf) and len(demand_pmf) == demand_hi+1), \
		"demand_pmf must be a list of length demand_hi+1 (or None)"

	# Determine y^*.
	if use_poisson:
		demand_pmf_dict = None
		y_star, _ = newsvendor_poisson(holding_cost, stockout_cost, demand_mean)
	else:
		demand_pmf_dict = {d: demand_pmf[d] for d in range(demand_hi+1)}
		y_star, _ = newsvendor_discrete(holding_cost, stockout_cost,
										demand_pmf=demand_pmf_dict)

	# Initialize.
	S0 = y_star
	s = y_star

	# Find s(S0).
	done = False
	while not done:
		s -= 1
		if use_poisson:
			gs = newsvendor_poisson_cost(s, holding_cost, stockout_cost, demand_mean)
		else:
			# TODO: build newsvendor_discrete_cost function
			gs = newsvendor_discrete(holding_cost, stockout_cost,
									 demand_pmf=demand_pmf_dict,
									 base_stock_level=s)[1]
		if s_s_cost_discrete(s, S0, holding_cost, stockout_cost, fixed_cost,
							 use_poisson, demand_mean, demand_hi, demand_pmf) \
			<= gs:
			done = True

	# Set s0.
	s0 = s

	# Initialize incumbent and cost.
	S_hat = S0
	s_hat = s0
	g_hat = s_s_cost_discrete(s_hat, S_hat, holding_cost, stockout_cost,
							  fixed_cost, use_poisson, demand_mean,
							  demand_pmf_dict)

	# Choose next order-up-to level to consider.
	S = S_hat + 1

	# Loop through S values.
	if use_poisson:
		gS = newsvendor_poisson_cost(S, holding_cost, stockout_cost, demand_mean)
	else:
		gS = newsvendor_discrete(holding_cost, stockout_cost,
								 demand_pmf=demand_pmf_dict,
								 base_stock_level=S)[1]
	while gS <= g_hat:

		# Check for improvement.
		if s_s_cost_discrete(s_hat, S, holding_cost, stockout_cost, fixed_cost,
							 use_poisson, demand_mean, demand_hi, demand_pmf) \
			< g_hat:

			# Update incumbent S.
			S_hat = S
			if use_poisson:
				gs = newsvendor_poisson_cost(s+1, holding_cost, stockout_cost,
											 demand_mean)
			else:
				gs = newsvendor_discrete(holding_cost, stockout_cost,
										 demand_pmf=demand_pmf_dict,
										 base_stock_level=s+1)[1]
			while s_s_cost_discrete(s, S_hat, holding_cost, stockout_cost,
									fixed_cost, use_poisson, demand_mean,
									demand_hi, demand_pmf) <= gs:
				s += 1
				if use_poisson:
					gs = newsvendor_poisson_cost(s + 1, holding_cost, stockout_cost,
												 demand_mean)
				else:
					gs = newsvendor_discrete(holding_cost, stockout_cost,
											 demand_pmf=demand_pmf_dict,
											 base_stock_level=s+1)[1]

			# Update incumbent s and g.
			s_hat = s
			g_hat = s_s_cost_discrete(s_hat, S_hat, holding_cost, stockout_cost,
									  fixed_cost, use_poisson, demand_mean,
									  demand_hi, demand_pmf)

		# Try next order-up-to level.
		S += 1
		if use_poisson:
			gS = newsvendor_poisson_cost(S, holding_cost, stockout_cost,
										 demand_mean)
		else:
			gS = newsvendor_discrete(holding_cost, stockout_cost,
									 demand_pmf=demand_pmf_dict,
									 base_stock_level=S)[1]

	s = s_hat
	S = S_hat
	g = g_hat

	return s, S, g
