from math import log, sqrt, pi, exp, erf
from numba import njit
from scipy.optimize import newton

"""
Black76 library for pricing and greeks.

Greeks and prices in this library are all undiscounted.
Discounting is to be done by the downstream user when necessary.
All prices and greeks except theta are easy to discount by multiplying by discount(T).
Greeks w.r.t. underlying are in the forward space, not spot.

NOTICE: I got this from Josh Kim. I did not write this code myself.
"""


@njit
def ndtr(x):
    return 0.5 * (1 + erf(x / sqrt(2.0)))


@njit
def normpdf(x):
    return exp(-0.5 * (x ** 2)) / sqrt(2 * pi)


@njit
def d1(sigma: float, strike: float, fwd: float, tau: float) -> float:
    return (-log(strike / fwd) + (0.5 * (sigma ** 2)) * tau) / (sigma * sqrt(tau))


@njit
def d2(d1: float, sigma, tau: float) -> float:
    return d1 - sigma * sqrt(tau)


################################
# Undiscounted Black 76 Prices #
################################


@njit
def b76_call(sigma: float, strike: float, fwd: float, tau: float) -> float:
    if strike == 0:
        return fwd
    if tau <= 0:
        return max(0.0, fwd - strike)
    _d1 = d1(sigma, strike, fwd, tau)
    return fwd * ndtr(_d1) - strike * ndtr(d2(_d1, sigma, tau))


@njit
def b76_put_from_call(call_price: float, strike: float, fwd: float, tau: float) -> float:
    if strike == 0:
        return 0.0
    if tau <= 0:
        return max(0.0, strike - fwd)
    return call_price - (fwd - strike)


@njit
def b76_put(sigma: float, strike: float, fwd: float, tau: float) -> float:
    if strike == 0:
        return 0.0
    call = b76_call(sigma, strike, fwd, tau)
    return b76_put_from_call(call, strike, fwd, tau)


@njit
def b76_price(sigma: float, strike: float, fwd: float, tau: float, is_call: bool):
    return b76_call(sigma, strike, fwd, tau) if is_call else b76_put(sigma, strike, fwd, tau)


@njit
def b76_prices(sigma: float, strikes: float, fwd: float, tau: float) -> tuple[float, float]:
    call = b76_call(sigma, strikes, fwd, tau)
    return call, b76_put_from_call(call, strikes, fwd, tau)


###################
# IV Root Finding #
###################


def iv_call_obj_function(sigma: float, strike: float, fwd: float, tau: float, premium_price: float):
    return b76_call(sigma, strike, fwd, tau) - premium_price


def iv_put_obj_function(sigma: float, strike: float, fwd: float, tau: float, premium_price: float):
    return b76_put(sigma, strike, fwd, tau) - premium_price


def vega_fprime(sigma: float, strike: float, fwd: float, tau: float, premium_price: float):
    return b76_vega(sigma, strike, fwd, tau)


# Wrapper function to calculate implied volatility
def iv_from_b76_price(
        premium_price: float, strike: float, tau: float, forward_price: float, is_call: bool, initial_guess: float = 1.0
) -> float:
    """
    Calculate the implied volatility using Newton Raphson.
    """
    try:
        if is_call:
            instrinsic_value = max(0.0, forward_price - strike)
            if premium_price >= forward_price:
                return 10.0
            elif instrinsic_value >= premium_price:
                return 0.0
            iv = newton(
                iv_call_obj_function,
                initial_guess,
                fprime=vega_fprime,
                args=(strike, forward_price, tau, premium_price),
                maxiter=100,
                tol=1e-4,
            )
        else:
            instrinsic_value = max(0.0, strike - forward_price)
            if premium_price >= strike:
                return 10.0
            elif instrinsic_value >= premium_price:
                return 0.0
            iv = newton(
                iv_put_obj_function,
                initial_guess,
                fprime=vega_fprime,
                args=(strike, forward_price, tau, premium_price),
                maxiter=100,
                tol=1e-4,
            )
    except RuntimeError:
        iv = 0.0

    return iv


################################
# Undiscounted Black 76 Greeks #
################################


@njit
def b76_delta(sigma: float, strike: float, fwd: float, tau: float, is_call: bool) -> float:
    """
    Forward black76 delta - multiply by basis=fwd/spot to get spot delta.
    """
    if strike == 0:
        return 1.0 if is_call else 0.0
    if tau <= 0:
        return 0.0
    _d1 = d1(sigma, strike, fwd, tau)
    return ndtr(_d1) if is_call else ndtr(_d1) - 1


@njit
def b76_gamma(sigma: float, strike: float, fwd: float, tau: float) -> float:
    """
    Forward black76 gamma - multiply by basis^2=(fwd/spot)^2 to get spot gamma.
    """
    if strike == 0:
        return 0.0
    if tau <= 0:
        return 0.0
    _d1 = d1(sigma, strike, fwd, tau)
    return normpdf(_d1) / (fwd * sigma * sqrt(tau))


@njit
def b76_vega(sigma: float, strike: float, fwd: float, tau: float) -> float:
    if strike == 0:
        return 0.0
    if tau <= 0:
        return 0.0
    _d1 = d1(sigma, strike, fwd, tau)
    return fwd * sqrt(tau) * normpdf(_d1)


@njit
def b76_theta(sigma: float, strike: float, fwd: float, tau: float) -> float:
    """
    Negative for longs, positive for shorts, per convention
    With non-zero rate, need to += rate x call (or put) price, then discount the sum
    """
    if strike == 0:
        return 0.0
    if tau <= 0:
        return 0.0
    _d1 = d1(sigma, strike, fwd, tau)
    return -fwd * normpdf(_d1) * sigma / (2 * sqrt(tau))


def warmup_jit():
    b76_price(1.0, 1.0, 1.0, 1.0, True)
    b76_prices(1.0, 1.0, 1.0, 1.0)
    b76_delta(1.0, 1.0, 1.0, 1.0, True)
    b76_gamma(1.0, 1.0, 1.0, 1.0)
    b76_vega(1.0, 1.0, 1.0, 1.0)
    b76_theta(1.0, 1.0, 1.0, 1.0)
