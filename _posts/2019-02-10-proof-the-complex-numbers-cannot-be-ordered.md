---
title: Proof the complex numbers cannot be ordered
description: This post demonstrates a mathematical proof that the complex numbers cannot be ordered. That is, there is no order we can impose on the complex field C.
---

In this post, we will demonstrate why the complex numbers, $$\mathbb{C}$$ cannot be ordered. That is, there is no sensible way we can use the "less-than" symbol ($$\lt$$) on two members of the complex field.

## Some background information on fields
You may have heard that the set of complex numbers endowed with operations for addition and multiplication $$\left( \mathbb{C}, +, \cdot \right)$$ are what's known as a **field**. That is, for all complex numbers $$z$$, $$z_1$$, $$z_2$$ and $$z_3$$, $$\mathbb{C}$$ has:
* **closure under addition**, that is $$z_1 + z_2$$ is also in $$\mathbb{C}$$,
* an **additive identity** (zero), $$0$$ having the property that $$z + 0 = z$$,
* **additive inverses** for all its elements, that is, a $$w$$ for each $$z$$ such that $$z + w = 0$$,
* **commutativity of addition**, that is $$z_1 + z_2 = z_2 + z_1$$,
* **associativity of addition**, that is $$\left( z_1 + z_2 \right) + z_3 = z_1 + \left( z_2 + z_3 \right)$$,
* **closure under multiplication**, that is $$z_1 \cdot z_2$$ is also in $$\mathbb{C}$$,
* a **multiplicative identity** (one), $$1$$ in $$\mathbb{C}$$ having the property that $$z \cdot 1 = z$$,
* **multiplicative inverses** for all its elements except $$0$$, that is, a $$w$$ for each $$z\neq 0$$ such that $$z \cdot w = 1$$,
* **commutativity of multiplication**, that is $$z_1 \cdot z_2 = z_2 \cdot z_1$$,
* **associativity of multiplication**, that is $$\left( z_1 \cdot z_2 \right) \cdot z_3 = z_1 \cdot \left( z_2 \cdot z_3 \right)$$, and
* **distributivity of multiplication over addition**, that is, $$z_1 \cdot (z_2 + z_3) = z_1 \cdot z_2 + z_1 \cdot z_3$$.

A good exercise is to verify all of the above properties hold for $$\mathbb{C}$$ with standard addition and multiplication to confirm it is indeed a field.

But why is being a field such a big deal? Knowing $$\mathbb{C}$$ is a field is enough for us to accept various theorems, processes, and discussions in other areas of mathematics as applicable in $$\mathbb{C}$$ as well. For example, linear algebra tells us that an element of any field can be used as a scalar in a vector space and, as a result, all of the theorems pertaining to vectors and scalars can now be accepted as true for complex numbers. Another example can be found in many helpful algebraic "tricks" or "shortcuts" we take for granted, such as using the FOIL method to multiply two binomials--this is really just making use of the distributivity of multiplication over addition. The fact is, we can do this with any field, not just $$\mathbb{R}$$.

## Ordered fields
That's not to say all properties of all fields are shared, otherwise there would be no reason for others to exist. One such property we cannot take for granted from other fields such as $$\mathbb{R}$$ is the notion of **order**.

For an ordering to exist, our field must have a notion of a **positive cone**, a strict subset $$P$$ of our field such that the following is true:
1. $$P$$ is closed under addition and multiplication, that is, for $$z_1$$ and $$z_2$$ in $$P$$, we have that both $$z_1 + z_2$$ and $$z_1 \cdot z_2$$ are also in $$P$$,
2. any element of the field multiplied by itself is in $$P$$. In other words, for any element of the field $$z$$, we have that $$z \cdot z$$ is in $$P$$,
3. any element of the field is either in $$P$$, its additive inverse is in $$P$$, or it is zero. In other words, for any element of the field $$z$$, either $$z$$ or $$-z$$ is in $$P$$, or $$z = 0$$.

Note that the above is indeed true in $$\mathbb{R}$$ if we take $$P$$ to be the natural numbers with zero and so the reals are ordered. In this article we will be examining a simple proof that the complex numbers, $$\mathbb{C}$$ are **not** ordered.

## The proof
Let's begin by supposing $$\mathbb{C}$$ is ordered. We will aim to arrive to a contradiction in the following steps to conclude that our assumption was wrong and that $$\mathbb{C}$$ is not ordered.

Let's consider the complex number $$i$$, the famous "imaginary" number having the property $$i^2 = -1$$.

* If $$i$$ is in $$P$$, then by point (2) in the definition above, $$i \cdot i = -1$$ is also in $$P$$. But then we have that $$-1 \cdot -1 = 1$$ is also in $$P$$ by point (2) again. So both $$-1$$ and $$1$$ are in $$P$$ but this directly contradicts point (3)! Therefore, $$i$$ cannot be in $$P$$.
* Similarly, if $$-i$$ is in $$P$$, then by point (2), $$-i \cdot -i = -1$$ is also in $$P$$ and we will arrive at the same contradiction to point (3) in this case. Therefore, $$-i$$ cannot be in $$P$$ either.

We have our contradiction, specifically to point (3)--neither $$i$$ nor $$-i$$ can be in $$P$$!

Therefore, the assumption must have been wrong and $$\mathbb{C}$$ must not be ordered after all.

## Followup questions
* $$\mathbb{C}$$ cannot have any concept of "positive" or "negative", it cannot be endowed with any ordering relations such as "less-than" or "greater-than". Can you construct any attempts at imposing order on the complex numbers regardless? This would arise to contradictions but think about maintaining as many field properties as possible by doing so.
* There are subsets of $$\mathbb{C}$$ which are ordered fields in and of themselves. See if you can find an example.