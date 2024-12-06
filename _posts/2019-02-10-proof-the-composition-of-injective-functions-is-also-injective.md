---
title: Proof the composition of injective functions is also injective
description: This mathematical proof shows the composition of two injective functions is also injective. The definition of function injectivity and composition is also covered.
---

{% include math.html %}

We are aiming in this proof to show that the composition of two injective functions is also injective. We will also go over the definition of function injectivity and composition.

Much of real and complex analysis and linear algebra are concerned with showing various functions have certain properties. This can enable you to jump to proven conclusions about these functions and use them to solve problems. Here is an example of how we can take two *injective* functions, call them $$f$$ and $$g$$ and show that their composition, $$f \circ g$$ is also injective.

## Injective?
An injective function is such that each element in the codomain is mapped to by no more than one element from the domain. To demonstrate this, suppose our function $$f$$ has a domain $$\{ 1, 2, 3 \}$$ and codomain $$\{ 4, 5, 6, 7, 8 \}$$. The following images demonstrate two hypothetical mappings performed by $$f$$, the first one being injective and the next one *not* being injective.

{% include img.html src="posts/2019/02/10/proof-the-composition-of-injective-functions-is-also-injective/injective-function.svg" alt="Injective function" %}
*Figure 1: Here $$f$$ is injective because each element in the codomain is mapped to by only either one or no element from the domain.*

{% include img.html src="posts/2019/02/10/proof-the-composition-of-injective-functions-is-also-injective/non-injective-function.svg" alt="Non-injective function" %}
*Figure 2: Here $$f$$ is not injective because the element $$5$$ in the codomain is being mapped to by two elements from the domain.*

Let’s try to formalise this definition of injectivity so that we can have something tangible to work with in the proof.

**Definition:** a function $$f$$ is injective if and only if every time $$f\left( x_1 \right) = f\left( x_2 \right)$$ we also have that $$x_1 = x_2$$.

Note that this is really capturing the idea that mappings in $$f$$ are **unique**—no two distinct elements of the domain can map to the same element in the codomain. In the above definition we are saying that if two elements of the domain have the same mapping, they must not be distinct.

## Composition of functions
Just to recap, the composition of two functions has the effect of applying one function first, and then feeding the output into the input of the next function. For example, if our functions are $$f$$ and $$g$$, then the composition of the two, written $$f \circ g$$ has the effect $$\left( f \circ g \right) \left( x \right) = f \left( g \left( x \right) \right)$$.

Note that for this to work, we need to have the range of $$f$$ (the set of values in the codomain that $$f$$ actually maps to) be a subset of the domain of $$g$$. In notational terms, we must have $$\mathrm{ran}\left( f\right) \subseteq \mathrm{dom}\left( g\right)$$.

## The proof
### (The composition of two injective functions is, itself, injective)
Remember, we are aiming in this proof to show that the composition of two injective functions is also injective. We will do so by assuming $$f$$ and $$g$$ are both injective. We will also assume that $$(f \circ g)(x_1) = (f \circ g)(x_2)$$ and then try to conclude that is only possible if $$x_1 = x_2$$. This directly appeals to the definition above of injectivity so will be a good strategy.

Suppose $$f$$ and $$g$$ are injective and $$(f \circ g)(x_1) = (f \circ g)(x_2)$$, i.e. $$f(g(x_1)) = f(g(x_2))$$. 

Since $$f$$ is injective, we must have $$g(x_1) = g(x_2)$$.

But $$g$$ is also injective, thus $$x_1 = x_2$$. 

Therefore $$f \circ g$$ is injective because and we have $$(f \circ g)(x_1) = (f \circ g)(x_2)$$ implying $$x_1 = x_2$$. 