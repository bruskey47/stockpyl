"""Code for solving newsvendor_normal problem.

Equation and section numbers refer to Snyder and Shen, "Fundamentals of Supply
Chain Theory", Wiley, 2019, 2nd ed., except as noted.

(c) Lawrence V. Snyder
Lehigh University and Opex Analytics

"""

import numpy as np
from scipy.stats import norm
from scipy.stats import poisson
from scipy.stats import nbinom
from scipy.integrate import quad
from types import *
from numbers import Number
from numbers import Integral

from pyinv.helpers import *


####################################################
# CONTINUOUS DISTRIBUTIONS
####################################################


def standard_normal_loss(z):
	"""
	Return :math:`\\mathscr{L}(z)` and :math:`\\bar{\\mathscr{L}}(z)`, the
	standard normal loss and complementary loss functions.

	Parameters
	----------
	z : float
		Argument of loss function.

	Returns
	-------
	L : float
		Loss function. [:math:`\\mathscr{L}(z)`]
	L_bar : float
		Complementary loss function. [:math:`\\bar{\\mathscr{L}}(z)]


	**Equations Used** (equations (C.22) and (C.23)):

	.. math::

		\\mathscr{L}(z) = \\phi(z) - z(1 - \\Phi(z))
		\\bar{\\mathscr{L}}(z) = z + \\mathscr{L}(z)

	**Example**:

	.. testsetup:: *

		from pyinv.loss_functions import *

	.. doctest::

		>>> standard_normal_loss(1.3)
		(0.04552796208651397, 1.345527962086514)

	"""

	L = norm.pdf(z) - z * (1 - norm.cdf(z))
	L_bar = z + L

	return L, L_bar


def standard_normal_second_loss(z):
	"""
	Return :math:`\\mathscr{L}^{(2)}(z)` and
	:math:`\\bar{\\mathscr{L}}^{(2)}(z)`, the standard normal second-order loss
	and complementary loss functions.

	Parameters
	----------
	z : float
		Argument of loss function.

	Returns
	-------
	L2 : float
		Loss function. [:math:`\\mathscr{L}^{(2)}(z)`]
	L2_bar : float
		Complementary loss function. [:math:`\\bar{\\mathscr{L}}^{(2)}(z)]


	**Equations Used** (equations (C.27) and (C.28)):

	.. math::

		\\mathscr{L}^{(2)}(z) = \\frac12\\left[\\left(z^2+1\\right)(1-\\Phi(z)) - z\\phi(z)\\right]

		\\bar{\\mathscr{L}}^{(2)}(z) = \\frac12(z^2 + 1) - \\mathscr{L}^{(2)}(z)

	**Example**:

	.. testsetup:: *

		from pyinv.loss_functions import *

	.. doctest::

		>>> standard_normal_second_loss(1.3)
		(0.01880706693657111, 1.326192933063429)

	"""

	L2 = 0.5 * ((z**2 + 1) * (1 - norm.cdf(z)) - z * norm.pdf(z))
	L2_bar = 0.5 * (z**2 + 1) - L2

	return L2, L2_bar


def normal_loss(x, mean, sd):
	"""
	Return :math:`n(x)` and :math:`\\bar{n}(x)``, the normal loss function and
	complementary loss functions for a :math:`N(\\mu,\\sigma^2)`
	distribution.

	Parameters
	----------
	x : float
		Argument of loss function.
	mean : float
		Mean of normal distribution. [mu]
	sd : float
		Standard deviation of normal distribution. [sigma]

	Returns
	-------
	n : float
		Loss function. [n(x)]
	n_bar : float
		Complementary loss function. [\bar{n}(x)]


	**Equations Used** (equations (C.31) and (C.32)):

	.. math::

		n(x) = \\mathscr{L}(z) \\sigma

		\\bar{n}(x) = \\bar{\\mathscr{L}}(z) \\sigma

	where :math:`z = (x-\\mu)/\\sigma`.

	**Example**:

	.. testsetup:: *

		from pyinv.loss_functions import *

	.. doctest::

		>>> normal_loss(18.6, 15, 3)
		(0.1683073521514889, 3.7683073521514903)

	"""
	z = (x - mean) / sd

	L, L_bar = standard_normal_loss(z)
	n = sd * L
	n_bar = sd * L_bar

	return n, n_bar


def normal_second_loss(x, mean, sd):
	"""
	Return :math:`n^{(2)}(x)` and :math:`\\bar{n}^{(2)}(x)``, the second-order
	normal loss function and complementary second-order loss function for a
	:math:`N(\\mu,\\sigma^2)` distribution.

	Parameters
	----------
	x : float
		Argument of loss function.
	mean : float
		Mean of normal distribution. [:math:`\\mu`]
	sd : float
		Standard deviation of normal distribution. [:math:`\\sigma`]

	Returns
	-------
	n2 : float
		Second-order loss function. [:math:`n^{(2)}(x)`]
	n2_bar : float
		Complementary second-order loss function. [:math:`\\bar{n}^{(n)}(x)`]

	**Equations Used** (equations (C.33) and (C.34)):

	.. math::

		n^{(2)}(x) = \\mathscr{L}^{(2)}(z) \\sigma^2

		\\bar{n}^{(2)}(x) = \\bar{\\mathscr{L}}^{(2)}(z) \\sigma^2

	where :math:`z = (x-\\mu)/\\sigma`.

	**Example**:

	.. testsetup:: *

		from pyinv.loss_functions import *

	.. doctest::

		>>> normal_second_loss(18.6, 15, 3)
		(0.21486028212500707, 10.765139717874998)

	"""
	z = (x - mean) / sd

	L2, L2_bar = standard_normal_second_loss(z)
	n = sd**2 * L2
	n_bar = sd**2 * L2_bar

	return n, n_bar


def lognormal_loss(x, mu, sigma):
	"""
	Return lognormal loss and complementary loss functions for logN(mu,sigma)
	distribution.

	Identities used:
		- n(x) = e^{mu+sigma^2/2} * Phi((mu+sigma^2-ln x)/sigma) -
			x(1 - Phi((ln x - mu)/sigma)); see equation (4.102)
		- \bar{n}(x) = x - E[X] + n(x); see equation (C.14)

	Notation below in brackets [...] is from Snyder and Shen (2019).

	Parameters
	----------
	x : float
		Argument of loss function.
	mu : float
		Mean of distribution of ln X.
	sigma : float
		Standard deviation of distribution of ln X.

	Returns
	-------
	n : float
		Loss function. [n(x)]
	n_bar : float
		Complementary loss function. [\bar{n}(x)]
	"""
	# Calculate E[X].
	E = np.exp(mu + sigma**2/2)

	if x > 0:
		n = E * norm.cdf((mu + sigma**2 - np.log(x)) / sigma) \
			- x * (1 - norm.cdf((np.log(x) - mu) / sigma))
		n_bar = x - E + n
	else:
		n = E - x
		n_bar = 0

	return n, n_bar


def continuous_loss(x, distrib):
	"""
	Return loss and complementary loss functions for an arbitrary continuous
	distribution.

	TODO: handle distribution supplied as pdf function

	Identities used:
		- n(x) = \int_x^\infty \bar{F}(y)dy; see equation (C.12)
		- \bar{n}(x) = \int_{-\infty}^x F(y)dy; see equation (C.13)

	Calculates integrals using numerical integration.

	Parameters
	----------
	x : float
		Argument of loss function.
	distrib : rv_continuous
		Desired distribution.

	Returns
	-------
	n : float
		Loss function. [n(x)]
	n_bar : float
		Complementary loss function. [\bar{n}(x)]
	"""
	# Find values lb and ub such that F(lb) ~ 0 and F(ub) ~ 1.
	# (These will be the ranges for integration.)
	lb = distrib.ppf(1.0e-10)
	ub = distrib.ppf(1.0 - 1.0e-10)

	# Calculate loss functions.
	n = distrib.expect(lambda y: max(y - x, 0), lb=x, ub=ub)
	n_bar = distrib.expect(lambda y: max(x - y, 0), lb=lb, ub=x)

	# Original version; the new version seems to be more accurate (and maybe
	# faster).
#	n = quad(lambda y: 1 - distrib.cdf(y), x, float("inf"))[0]
#	n_bar = quad(lambda y: distrib.cdf(y), -float("inf"), x)[0]

	return n, n_bar


####################################################
# DISCRETE DISTRIBUTIONS
####################################################

def poisson_loss(x, mean):
	"""
	Return Poisson loss and complementary loss functions for Pois(mu)
	distribution.

	Identities used:
		- n(x) = -(x - mu)\bar{F}(x) + mu * f(x); see equation (C.41)
		- \bar{n}(x) = (x - mu) * F(x) + mu * f(x); see equation (C.42)

	Raises ValueError if x is not an integer.

	Parameters
	----------
	x : float
		Argument of loss function.
	mean : float
		Mean of Poisson distribution.

	Returns
	-------
	n : int
		Loss function. [n(x)]
	n_bar : float
		Complementary loss function. [\bar{n}(x)]
	"""
	# Check for integer x.
	assert is_integer(x), "x must be an integer"

	n = -(x - mean) * (1 - poisson.cdf(x, mean)) + mean * poisson.pmf(x, mean)
	n_bar = (x - mean) * poisson.cdf(x, mean) + mean * poisson.pmf(x, mean)

	return n, n_bar


def negative_binomial_loss(x, mean, sd):
	"""
	Return negative binomial loss and complementary loss functions for NB
	distribution with given mean and standard deviation.

	(Function calculates n and p, the NB parameters.) Assumes mu < sigma^2.

	Identities used:
		- n(x) = -(x - n*beta)\bar{F}(x) + (x + n) * beta * f(x), where
			beta = p/(1-p); see Zipkin (2000), Section C.2.3.6.
		- \bar{n}(x) = x - E[X] + n(x); see equation (C.14)

	Raises ValueError if x is not an integer.

	Parameters
	----------
	x : float
		Argument of loss function.
	mean : float
		Mean of NB distribution.
	sd : float
		Standard deviation of NB distribution.

	Returns
	-------
	n : int
		Loss function. [n(x)]
	n_bar : float
		Complementary loss function. [\bar{n}(x)]
	"""
	# Check for integer x.
	assert is_integer(x), "x must be an integer"

	r = 1.0 * mean ** 2 / (sd ** 2 - mean)
	p = 1 - (sd ** 2 - mean) / (sd ** 2)
	beta = p / (1 - p)

#	return discrete_loss(x, nbinom(r, p))
#	n = -(x - r * beta) * (1 - nbinom.cdf(x, r, p)) + (x + r) * beta * nbinom.pmf(x, r, p)
#	n_bar = x - mean + n
	# formula above does not seem to be working (e.g., if r = 6, p = 0.4, then
	# returns negative value for n(10). So for now, using generic function:
	n, n_bar = discrete_loss(x, nbinom(r, p))

	return n, n_bar


def discrete_loss(x, distrib=None, pmf=None):
	"""
	Return loss and complementary loss function for an arbitrary discrete
	distribution.

	Must provide either rv_discrete distribution (in distrib) or
	demand pmf (in pmf, as a dict).

	Assumes cdf(x) = 0 for x < 0.

	Identities used: (C.36), (C.37)

	Raises ValueError if x is not an integer.

	Parameters
	----------
	x : int
		Argument of loss function.
	distrib : rv_discrete, optional
		Desired distribution.
	pmf : dict, optional
		pmf, as a dict in which keys are the support of the distribution and
		values are their probabilities. Ignored if distrib is not None.

	Returns
	-------
	n : float
		Loss function. [n(x)]
	n_bar : float
		Complementary loss function. [\bar{n}(x)]
	"""
	# Check for integer x.
	assert is_integer(x), "x must be an integer"

	# Check that either distribution or pmf have been supplied.
	assert (distrib is not None) or (pmf is not None), "must provide distrib or pmf"

	if distrib is not None:
		# rv_discrete object has been provided.
		n_bar = np.sum([distrib.cdf(range(int(x)))])
		n = n_bar - x + distrib.mean()

		# Old (slower) method:
		# n = 0.0
		# y = x
		# comp_cdf = 1 - distrib.cdf(y)
		# while comp_cdf > 1.0e-12:
		# 	n += comp_cdf
		# 	y += 1
		# 	comp_cdf = 1 - distrib.cdf(y)
		#
		# n_bar = 0.0
		# for y in range(0, int(x)):
		# 	n_bar += distrib.cdf(y)
	else:
		# pmf dict has been provided.
		x_values = list(pmf.keys())
		x_values.sort()
		# TODO: vectorize this
		n = np.sum([(y - x) * pmf[y] for y in x_values if y >= x])
		n_bar = np.sum([(x - y) * pmf[y] for y in x_values if y <= x])

	return n, n_bar
