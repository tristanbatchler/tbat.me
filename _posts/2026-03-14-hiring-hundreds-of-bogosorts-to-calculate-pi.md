---
title: Hiring hundreds of bogosorts to calculate pi
description: Happy Pi Day! This fine morning I woke up and felt the sudden urge to torture my CPU. And what batter way to do that than run hundreds of instances of one of the most notoriously inefficient sorting algorithms at once?
redditurl: https://www.reddit.com/r/math/comments/m6obwp/this_year_i_calculated_pi_by_finding_the_area
---

{% include math.html %}

Happy Pi Day! This fine morning I woke up and felt the sudden urge to
torture my CPU.

And what better way to do that than run hundreds of instances of one of
the most notoriously inefficient sorting algorithms at once?

Of course the algorithm I speak of is...

## Bogosort 

In the world of sorting algorithms, bogosort is kind of the 
laughingstock of the town. The village idiot. He's just...not that 
bright. How does it work?

> *Take a list of size $$n$$ and randomly shuffle it until it's sorted
> purely by chance.*

Yeah, like I said, not too clever of an algorithm. Though, technically
it *is* a way to sort a list.

Love it or hate it, this bad boy can sort a list in a quite frankly
impressive $$n!$$ shuffles on average.

Recall the *factorial* of $$n$$, written as $$n!$$ is the simple product
$$n (n-1) (n-2) \cdots (2) (1)$$. The reason we can expect bogosort to do
its job in $$n!$$ shuffles is the same reason a list can be organised in
$$n!$$ ways. We wouldn't expect bogosort to need to perform more or less
than the total possible number of ways to arrange the items in the list,
within a reasonable margin of good/back luck of course.

For the nerds, since a shuffle requires $$n$$ moves, and we need $$n!$$ of
these, bogosort's time complexity is an eye-watering
$$\mathcal{O}(n \cdot n!)$$. So yeah, it's impressive in the same way one
might be impressed with a monkey on a typewriter producing anything
legible.

All this yapping and we're not any closer to seeing what any of this has
to do with pi, are we? Fine, let me cut to the chase and introduce our
smoking gun; our key to unlocking the digits of pi (hopefully).

## Stirling's Approximation 

Here it is:

$$
	n! \sim \sqrt{2 \pi n} \left( \frac{n}{e} \right)^n
$$

You might be able to guess we can obtain $$\pi$$ as long as we have access
to $$n$$ and $$n!$$, but let's not get ahead of ourselves. We should talk
about this formula.

First, let's look at that squiggly little guy ($$\sim$$). In this case, we
use this to denote that the two sides are *asymptotically equivalent*:
essentially as $$n$$ grows arbitrarily large, the right-hand side becomes
a better and better approximation for the left. So just think for large
$$n$$, we can think of $$\sim$$ as $$\approx$$ (this is probably an abuse of
notation and for legal reasons I cannot recommend this).

## Why on earth does this formula work? 

Before we go any further, it might be nice to wave a few hands and run a
few sanity checks to convince ourselves this Stirling guy wasn't some
kind of fraud. I'm not going to try and fumble my way through a full
proof, but want to at least see if I can convince you that this is
reasonable enough to believe.

First, let's look at the natural logarithm of $$n!$$ so we can work with
sum of terms, rather than a product. It'll make it easier to work with
that way.

$$
    \ln(n!) = \ln(1) + \ln(2) + \dots + \ln{n} = \sum_{x=1}^{n} \ln{x}
$$

That should be fairly obvious, but what might not be is the fact that
this looks like one of those "introduction to integrals" demonstrations
you might have seen in high school. You approximate a curve but slicing
it into a bunch of skinny rectangles and calculate the area under the
curve to be the sum of the areas of those rectangles, right?

Well, doesn't $$\ln(n!)$$ look like an approximation of
$$\int_1^n \ln{x} dx$$ to you? Just rectangles of width $$1$$.

Re-familiarising myself with some of the most boring calculus I forgot,
we can solve this integral using integration by parts:

$$
	\sum_{x=1}^{n} \ln{x} \approx \int_{1}^{n} \ln{x} \, dx = \Big[ x \ln{x} - x \Big]_{1}^{n} = n \ln{n} - n + 1
$$

If we exponentiate both sides to undo our logarithm, we get

$$
\begin{align*}
    n! &\approx \exp\left(n \ln{n} - n + 1\right) \\
       &= \exp\left(n \ln{n}\right) \cdot \exp\left(-n\right) \cdot \exp\left(1\right) \\
       &= n^n \cdot e^{-n} \cdot e \\
       &= e \cdot \left( \frac{n}{e} \right)^n
\end{align*}
$$

Look at that! We are already remarkably close to Stirling's actual
formula. The only difference is that we have a factor of $$e$$ in front of
the $$\left( \frac{n}{e} \right)^n$$ term, whereas Stirling's formula has
$$\sqrt{2 \pi n}$$ instead.

But if we observe that $$\sqrt{2 \pi} \approx e$$, we see our calculation
is accurate up to a factor of $$\sqrt{n}$$ which isn't bad considering we
just approximated a sum with an integral.

So hopefully that's enough to let us move on with confidence that
Stirling's approximation will give us the horsepower for what we want to
do. Speaking of which, let's get to the good stuff.

## Where does the $$\pi$$ come from?

Let's just forget I totally hand-waved the $$\pi$$ out of Stirling's formula 
in my crude explanation above. It's really there, but it's quite tricky to 
derive it. In fact, Stirling didn't even come up with the idea for this 
formula, he simply decided the constant in front of the 
$$\left( \frac{n}{e} \right)^n$$ term was indeed $$\sqrt{2 \pi n}$$. It was 
originally derived by [De Moivre](https://en.wikipedia.org/wiki/Abraham_de_Moivre).

To give a very rough idea of how $$\pi$$ snaked its way into this formula, 
we can thank how the Gamma function connects factorials to integrals.

$$
    n! = \Gamma(n+1) = \int_0^\infty t^n e^{-t} dt
$$

It turns out, when you make this connection and continue to solve the 
integral using some clever observations about logarithms and Taylor series, 
you'll find $$\pi$$ emerge in the final steps of the proof. If you're interested, 
in the details, I'd recommend checking out 
[this question on Math Stack Exchange](https://math.stackexchange.com/questions/2965792/is-there-an-intuitive-explanation-for-the-occurrence-of-e-and-pi-in-stirlings-a).

## A hand-wavy approximation of $$\pi$$ 

Now, let's just dust off some high school algebra and isolate $$\pi$$, and
I'll use the $$\approx$$ sign here because we can assume we are talking
about a sufficiently large $$n$$ <small>(what constitutes "sufficiently large" 
in this case? i'll let you decide)</small>.

$$
    \begin{align*}
        \sqrt{2 \pi n} \left( \frac{n}{e} \right)^n &\approx n!\\
        \sqrt{2 \pi n} &\approx n! \left( \frac{e}{n} \right)^n\\
        2 \pi n &\approx n!^2 \left( \frac{e}{n} \right)^{2n}\\
        \pi &\approx \frac{n!^2}{2n} \left( \frac{e}{n} \right)^{2n}
    \end{align*} 
$$

Here's where my evil plan gets legs. I'm too lazy to calculate $$n!$$ directly, 
so I'll just coerce my CPU into fetching it for me, and then I'll *that* value 
to estimate $$\pi$$.

## Exercising free will by obtaining $$n!$$ empirically, for some reason 

Here is where the dunce up my sleeve, bogosort, gets to shine.

As previously discussed, the number of shuffles expected for bogosort to
sort a list is $$n!$$, which means we get a way of counting $$n!$$ without
having to do the computation ourselves.

Instead, we will employ hundreds of bogosort algorithms to sort hundreds
of lists, until we are satisfied with our average, our approximation for
$$n!$$.

Why would we do that when instead we could just calculate directly
$$n (n-1) \cdots (2) (1)$$? It's a free country, I can make my CPU do
whatever I want!

Anyway, suppose we do this, and obtain an average number of shuffles for
a list of size $$n$$. We'll call this $$S$$.

Plugging our hard-earned $$S$$ back into our beautiful, Frankenstein's
monster of an equation, we get our official Bogosort-$$\pi$$ estimator:

$$
	\pi \approx \frac{S^2}{2n} \left( \frac{e}{n} \right)^{2n}
$$

The plan is as follows: pick a huge $$n$$, run bogosort millions of
times to get a rock-solid average $$S$$, and calculate $$\pi$$ to a glorious
number of decimal places just in time to eat some pie and celebrate
March 14.

And obviously the accuracy of our result relies on choosing a
sufficiently large $$n$$ to satisfy the gods of asymptotic analysis.

Except...wait. The larger $$n$$ is, the longer bogosort will take to
complete. At a worse-than-exponential rate.

## Competing objectives 

Thanks to that eye-watering $$\mathcal{O}(n \cdot n!)$$ time complexity,
choosing an appropriate $$n$$ could mean the difference between our CPU
finishing the task in a reasonable amount of time, and it dwarfing the
age of the universe.

To put things into perspective, let's choose a modest $$n := 20$$ for our
experiment. The expected number of swaps required to sort this once with
our good friend bogosort is on the order of $$20 \cdot 20!$$, which comes
out to 40 quintillion, or 40 billion billion (fun fact: this is roughly
the number of configurations of the Rubik's cube). Let's be generous and
suppose our CPU can perform 40 billion swaps per second (my best attempt
at benchmarking this on a Ryzen 7 9700X was about 4 billion swaps per
second, but let's be optimistic). This means that we'd be looking at 1
billion seconds, or 32 years, to sort a single list. And that's assuming
we get the average case scenario, which is completely at the mercy of
the random number generator. Hmm...maybe I could schedule this post to
be published in time for Pi Day 2058?

No, let's see what happens if we choose $$n := 10$$ instead. Remember when
I said $$n$$ should be "sufficiently large"? If you ask me, 10 is pretty 
up there. Definitely one of the bigger numbers I've seen. Anyway, let's 
roll with it. No further questions.

Since $$10 \cdot 10!$$ is only about 36 million, I like our chances of
getting this one done in time. In fact, we can even run it over and over
again comfortably to get a good average for our $$S \approx 10!$$. I like
this as a testament to the growth of the factorial function, how
dramatically different the output is from just $$n := 10$$ to $$n := 20$$.

## The plan 

Anyway, I believe I'm yapping again. Let's summarise the plan for
approximating $$10!$$ and then using that to estimate $$\pi$$:

> Repeat the following $$K$$ times (where $$K$$ is as many as you have the
> patience for):
> -   run bogosort on a list of size 10, keeping track of the number of
>     shuffles required, let's call this $$s$$;
> -   increment $$S$$ by $$s / K$$, as to contribute to our running average.

If you prefer, we can write this in concrete C code. This is exactly how
I implemented it, and my $$K$$ was 320 which is obtained by multiplying my
number of CPU cores (16) by the number of trials I wanted to run on each
core (20). I parallelised the code to squeeze as much bogosort out of my
CPU as I could, but for the sake of simplicity, here is a
single-threaded version of the code:

```c
#include <stdio.h>
#include <math.h>

#define N 10
#define K 320

int main() {
    long long total_shuffles = 0;

    for (int t = 0; t < K; t++) {
        int arr[N] = {4, 2, 9, 1, 5, 3, 8, 6, 10, 7};

        long long s = 0;
        while (!is_sorted(arr, N)) {
            shuffle(arr, N);
            s++;
        }
        total_shuffles += s;
        printf("Trial %d completed. Shuffles: %lld\n", t, s);
    }

    // Calculate our empirical average
    double S = (double)total_shuffles / K;
    
    // Calculate Pi using our Bogosort-derived S
    double e = exp(1.0);
    double pi = (S * S) / (2 * N) * pow(e / N, 2 * N);

    printf("Empirical S (average shuffles): %f\n", S);
    printf("Estimated value of pi: %f\n", pi);

    return 0;
}
```

If you're interested everything in this write-up, including the code, is
available on the GitHub repository.

## The moment of truth 

Running the above C code, and depending on your luck...

    $ gcc main.c -o bogopi -lm
    $ ./bogopi

    Trial 0 completed. Shuffles: 1677134
    Trial 1 completed. Shuffles: 7093752
    Trial 2 completed. Shuffles: 708255
    Trial 3 completed. Shuffles: 1584920
    ...
    Trial 318 completed. Shuffles: 3490385
    Trial 319 completed. Shuffles: 5376543
    Empirical S (average shuffles): 3611139.253125
    Estimated value of pi: 3.163356

Hey, that's pretty good! Especially considering our bogosorts did their
job on average in 3,611,139 shuffles, and we know the *real* $$10!$$ is
3,628,800. Being within 0.49% of the true factorial is a fantastic
result.

For the visual-minded, here's a little animation I whipped up in 
[Manim](https://www.manim.community/) to show the process.

<video controls video muted playsinline>
  <source src="/assets/images/posts/2026/02/23/BogoSortGrid.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

So now we can all go home and rest easy knowing that
$$\pi \approx 3.163356$$ according to the consensus of 320 bogosorts...
right?

## The ceiling 

Wait a minute.

Suppose, just for a moment, that our bogosort was *perfect*. Suppose it
wasn't subject to the whims of a random number generator, and it gave us
the exact, mathematically precise value for $$10!$$, with zero error. What
would happen?

Well, even with a perfect $$n!$$, Stirling's approximation is still only
an approximation. It converges to the true value as $$n \to \infty$$, but
$$n = 10$$ is decidedly not infinity. In fact, if we plug the exact value
of $$10! = 3{,}628{,}800$$ into our formula, we get:

$$
    \pi \approx \frac{3628800^2}{2 \cdot 10} \left( \frac{e}{10} \right)^{20} = 3.1944\dots
$$

That's 1.68% above the true $$\pi = 3.14159\dots$$, and there's absolutely
nothing we can do about it. No amount of bogosort trials will fix this.
It's baked into the formula itself.

This 1.68% is the theoretical floor on our error at $$n = 10$$. For larger
$$n$$, Stirling's approximation gets better: at $$n = 50$$ the floor drops
to 0.33%, and at $$n = 100$$ it's 0.17%. But as we've already established,
we can't *use* large $$n$$ because bogosort won't finish before the heat
death of the universe.

## Error propagation (why $$S^2$$ is our unpredictable "friend") 

To make matters worse, notice that our formula squares the bogosort
average ($$S$$):

$$
    \pi \approx \frac{S^2}{2n} \left( \frac{e}{n} \right)^{2n}
$$
By the standard rules of error propagation, when a measured quantity is
squared, the relative error in the result is doubled.

So if bogosort underestimates $$10!$$ by 0.5%, our $$\pi$$ estimate shifts
by about 1.0%. This means any empirical noise we generate is amplified
on top of the 1.68% theoretical floor we are already stuck with.

This could work in our favour, however, if bogosort *underestimates*. In
that case, it would actually be nudging our estimate closer to the true
value of $$\pi$$, potentially cancelling out Stirling's floor.

Turns out two wrongs *can* make a right, but I don't feel good about it.

## It's time for me to come clean 

It's time for me to confess: the only way to get a \"good\" estimate of
$$\pi$$ using this method is to be actively, deliberately lucky. But not
too lucky! Let me explain.

Because Stirling's formula has a built-in overestimate for $$\pi$$, we
actually *want* our bogosort trials to finish early. We need them to hit
the sorted array faster than they mathematically should, artificially
cutting our $$S$$ value down just enough so that when it gets squared, it
drags Stirling's approximation for $$\pi$$ back down enough to look like
the whole system works.

In my case, I simply kept running the experiment with $$n := 10$$ and
$$K := 320$$ until I saw a result I was happy with.

The *average* of many runs will eventually land our $$S$$-value close to
the true $$10!$$ (which ironically, ruins our $$\pi$$ estimate by pushing it
back up to 3.19). But any single attempt of 320 trials is a complete
roll of the dice. You are entirely at the mercy of RNG.

## The verdict 

So, is this a good way to calculate $$\pi$$? Just kidding, I know nobody
is still reading and asking that question. But for the record, here's a
summary of everything working against us:
-   Stirling's approximation needs a large $$n$$ to be accurate, but
    bogosort needs a small $$n$$ to actually, you know, complete in time
    for Pi Day.
-   At $$n = 10$$, Stirling's formula has a built-in 1.68% overestimate
    that no amount of trials can fix.
-   The squaring of $$S$$ doubles any empirical noise.
-   The only way to accidentally land near the true $$\pi$$ is if our
    bogosort gets slightly *unlucky* at estimating $$n!$$ (but not too
    much!) to cancel Stirling's bias.

We are using one of the worst possible sorting algorithms to fuel an
asymptotic approximation at values where it is not yet asymptotic, and
the only path to a correct answer is through a lucky coincidence of
offsetting errors.

Even so, the fact that 320 instances of an algorithm that sorts by pure
random chance can even semi-consistently produce a number that starts
with the digit $$3$$ should be celebrated. Happy Pi Day!
