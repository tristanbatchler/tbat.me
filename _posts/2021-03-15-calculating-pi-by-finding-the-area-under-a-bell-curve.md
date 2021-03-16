---
layout: post
title: Calculating Pi by finding the area under a bell curve
description: For Pi Day in 2021, I decided to use a lesser-known method of
  calculating the digits of Pi.
---


## Recap on probability density functions
In statistics, a **probability density function** (**PDF**) of a continuous random variable $$r$$ is a curve whose height, at any given sample along the $$x$$-axis, represents the relative likelihood that $$r$$ equals that sample.

For example, take $$r$$ to be a random stranger's height in inches. Now suppose the PDF of $$r$$ looks like this:
![Injective function](/assets/css/images/posts/2021/03/16/calculating-pi-by-finding-the-area-under-a-bell-curve/pdf.svg)

What this curve tells us is the probability this random stranger's height is around $$68"$$ is relatively high. The chance their height is above $$75"$$ or below $$60"$$ is more unlikely.

The mean average height of strangers is exacly in the centre peak of this PDF, while about $$95\%$$ of the values lie within two standard deviations. It turns out this PDF is exactly the kind of shape of a **normal distribution** or **bell curve**.

## On normal distributions
A normal distribution is the kind of distribution you get with a large number of independent samples of a random variable. For example, the heights or weights of random citizens picked off a street.

The general form of normal distribution's PDF is
$$$$
    y = \frac{1}{\sigma \sqrt{2 \pi}} e^{-\frac{1}{2}\left( \frac{x - \mu}{\sigma} \right)^2}
$$$$
where $$\mu$$ is the mean of the distribution, and $$\sigma$$ is the standard deviation. 

## The area under a normal distribution
The factor of $$1/\left( \sigma \sqrt{2 \pi} \right)$$ ensures the area under this curve is exactly $$1$$. The area **must be** $$1$$ since it is the sum of probabilities in a distribution. Without this factor, the peak of the graph would be $$1$$ and the total area would be $$\sigma \sqrt{2 \pi}$$. This is because we have
$$$$
    \int_{-\infty}^{\infty} {\frac{1}{\sigma \sqrt{2 \pi}} e^{-\frac{1}{2}\left( \frac{x - \mu}{\sigma} \right)^2}} = 1,
$$$$
so, moving the constant factor out of the integral and dividing it through on both sides gives
$$$$
    \int_{-\infty}^{\infty} e^{-\frac{1}{2}\left( \frac{x - \mu}{\sigma} \right)} = \sigma \sqrt{2 \pi}.
$$$$
![Injective function](/assets/css/images/posts/2021/03/16/calculating-pi-by-finding-the-area-under-a-bell-curve/denormalised-pdf.svg)
*Figure 2: The PDF from before, but without the normalisation factor, making its peak 1 and its area a factor of $$\sqrt{2\pi}$$.*
