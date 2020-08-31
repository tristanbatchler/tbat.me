---
title: An infinite convergent sequence of integers?
description: My brother recently had an interesting question on his introductory analysis assignment. What can we say about an infinite sequence of integers which converges? An intuitive idea which turns out to be quite tricky to prove.
---

My brother recently had an interesting question on his introductory analysis assignment. What can we say about an infinite sequence of integers which converges? An intuitive idea which turns out to be quite tricky to prove.

## The problem
My brother recently had an interesting question on his introductory analysis assignment:
> Suppose $$\{ a \}_{i=1}^\infty$$ is a convergent sequence of integers. Prove the existence of some $$N \in \mathbb{N}$$ such that, for all $$i, j \geq N$$, $$a_i = a_j$$.

In other words, at some point in the sequence, there is just an infinite run of the same number.

For example, let $$a_i := \lfloor 8 / i \rfloor$$. In this case, the sequence is $$8, 4, 2, 2, 1, 1, 1, 1, 0, 0, 0, ...$$ and so on with zeros following forever.

I think we can explore a quick proof of this very intuitive idea. I find sometimes the hardest part of a proof is detaching yourself from your intuition, your "of course that's true" mentality. Some facts are just so seemingly obvious, even trivial, but it is still important to demonstrate a rigorous proof of these facts. Without further ado, here it is.

## The proof
Recall the definition of sequence convergence:
> A sequence $$\{a\}_{i=0}^\infty$$ is said to converge to $$L$$ if and only if: for all $$\epsilon > 0$$, there exists some $$N > 0$$ such that $$\vert a_n - L\vert < \epsilon$$ whenever $$n > N$$.

So let's take $$\epsilon$$ to be, say, $$1/4$$. We already know our sequence converges, so we can say there exists some $$N > 0$$ such that $$\vert a_n - L\vert < 1/4$$ whenever $$n > N$$.

Now note that $$\vert a_i - a_j\vert = \vert a_i - L + L - a_j\vert $$. Using the triangle inequality, we conclude that $$\vert a_i - a_j\vert \leq \vert a_i - L\vert + \vert L - a_j\vert $$.

Let $$i, j > N$$ so that $$\vert a_i - L\vert , \vert L - a_j\vert < 1/4$$. Therefore $$\vert a_i - a_j\vert \leq \vert a_i - L\vert + \vert L - a_j\vert < 1/4 + 1/4 = 1/2$$.

So in the end, we have $$\vert a_i - a_j\vert < 1/2$$.

But remember: $$a_i$$ and $$a_j$$ are integers! What can we way about integers who are less than $$1/2$$ apart? They must be equal!

## Remarks
This is a classic example of a "mean" question. It's conceptually very easy to understand and frustratingly intuitive ("why do I need to bother explaining this?"). The tools required for the proof are all accessible to a student in introductory analysis, but the proof requires a few clever points for it to all come together. For example, what maths beginner is going to conjure the magic number $$1/4$$ to assign to $$\epsilon$$ or think of invoking the fact that $$\vert a_i - a_j\vert = \vert a_i - L + L - a_j\vert $$? Only students who are accustomed to those "tricks" will know how to take advantage of something as nuanced as that.

These are perfect questions for separating the good students from the excellent students and therefore are necessary to obtain a fair grade distribution in your class.

As a final note, don't be discouraged from this. Remember, there is **always** more than one angle of attack for a proof. It may be the case that your professor is looking for one particular angle of attack, but that doesn't mean it's the only one you should be aiming for. If you are stuck on a problem and are getting nowhere, take a walk, clear your head, and start again. There is no such thing as a "loss of progress" when you're restarting a maths problem. The more angles you've explored the closer you're narrowing in to the solution.