---
title: What's the angle between a clock's hands given the current time?
description: A clock shows the current time as, say, 4:20. What is the angle between the hour and minute hands?
redditurl: https://www.reddit.com/r/learnmath/comments/q090bz
---

Here's kind of a fun and interesting question.

A clock shows the current time as, say, 4:20. What is the angle between the hour and minute hands? What about in general? Is there a nice formula we can use to get this angle given any time? And does this have any applications?

![Clock showing 4:20](/assets/css/images/posts/2021/10/02/what-is-the-angle-between-a-clocks-hands-given-the-current-time/Clock_04-20.svg)
*Figure 1: Oh would you look at the time*

## Worked example
If it's currently 4:20, then the minute's hand is $$\frac{20}{60}$$ of a full revolution. Since there are $$360^\circ$$ in a full revolution, the angle of the minute's hand (with respect to the top of the clock) is $$\frac{20}{60}\cdot 360^\circ = 120^\circ$$.

Furthermore, we know the hour hand would be $$\frac{4}{12}$$ of a full revolution **if** it were simply 4:00. But we need to account for the amount the hour hand moved in 20 minutes as well, so the angle of the hour hand will be $$\frac{4}{12} \cdot 360^\circ + \text{a bit}$$. What is *a bit*, though? Well the hour hand will move exactly another $$\frac{1}{12}$$ of a revolution in 60 minutes. So in 20 minutes, it will only have moved a third that amount, e.g. $$\left( \frac{1}{3} \cdot \frac{1}{12}\right) \cdot 360^\circ = \frac{1}{36} \cdot 360^\circ = 10^\circ$$. Putting everything together, the hour hand is at an angle of $$\frac{4}{12} \cdot 360^\circ + \text{a bit} = 120^\circ + 10^\circ = 130^\circ$$.

The angle between the hour and minute hands, therefore, is simply the difference between their individual angles with respect to the top of the clock, i.e. $$130^\circ - 120^\circ = 10^\circ$$.

## The general formula
Let $$h \in \mathbb{Z}_{12}$$ be the current hour and $$m \in \mathbb{Z}_{60}$$ is the current minute.

For example, if the current time is 4:20, then $$h = 4$$ and $$m = 20$$. If, instead, the time is 12:00, then $$h = m = 0$$.

Now, just as before, we will find each respective angle of the hands with respect to the top of the clock. Note that we will continue to work in degrees rather than radians for a couple of reasons:
1. The numbers on the clock, 12, and the number of ticks, 60 are both factors of 360, the number of degrees in a full revolution. Continuing to work in degrees will make the math a bit nicer.
2. Any computer programming applications of this result will work nicer with a formula involving as little floating point representations of numbers as possible. Numbers like $$\pi$$ don't calculate well with other numbers in the CPU and can potentially lead to slower and less precise results.

Let $$\alpha_m \in \mathbb{R} \cap \left[ 0, 360 \right)$$ denote the angle of the minute hand with respect to the top of the clock. Similarly $$\alpha_h$$ denotes the angle of the hour hand.

### The minutes hand $$\alpha_m$$
We know there are 60 minutes in a revolution, so $$\alpha_m = \frac{m}{60} \cdot 360^\circ = 6m^\circ$$.

### The hours hand $$\alpha_h$$
As before, the angle of the hour hand is going to be $$\frac{h}{12} \cdot 360^\circ + \text{a bit}$$.

Here, *a bit* is the "fraction" of $$\frac{1}{12}$$ a revolution; the "fraction" being the "progress" of the minute's hand, i.e. $$\frac{m}{60}$$. In other words: 

$$
\begin{align*}
\text{a bit} &= \left(\frac{1}{12} \cdot 360^\circ \right) \cdot \frac{m}{60} \\
             &= \left( 30^\circ \right) \cdot \frac{m}{60} \\
             &= \frac{m}{2}^\circ
\end{align*}
$$. 

Altogether, $$\alpha_h = \frac{h}{12} \cdot 360^\circ + \frac{m}{2}^\circ = \frac{60h + m}{2}^\circ$$.

### The angle between them

$$
\begin{align*}
\alpha_h - \alpha_m &= \frac{60h + m}{2}^\circ - 6m^\circ \\
                    &= \frac{60h + m}{2}^\circ - \frac{12m}{2}^\circ \\
                    &= \frac{60h - 11m}{2}^\circ
\end{align*}
$$.

Therefore, our general formula for the angle between hands on a clock (in degrees) given $$m$$ minutes and $$h$$ hours, is:
$$
\theta = \frac{60h - 11m}{2}^\circ
$$

## Sanity check
Let's test our example from before with our general formula. We already know the angle between hands on a clock at 4:20 is just $$10^\circ$$. Let's just make sure our formula gives the same result.

Let $$m = 20$$, $$h = 4$$. Then:
$$
\theta = \frac{60h - 11m}{2}^\circ = \frac{60 \cdot 4 - 11 \cdot 20}{2}^\circ = \frac{20}{2}^\circ = 10^\circ
$$
which is exactly what we wanted to see ✔

## Applications?
It might be useful if you're simply wanting to draw an accurate clock for given a time, but our two intermediary results are probably more useful for this:
$$
\alpha_m = 6m^\circ \\
\alpha_h = \frac{60h + m}{2}^\circ
$$

These two formulas will tell you which angle to draw the lines at (with respect to the top of the clock).

Here's a quick, interactive demo written in [p5.js](https://p5js.org/):
<div id="demo" style="margin-left: auto; margin-right: auto; width: 100%; max-width: 400px; overflow-x: auto;">
    <main></main>
    <table style="margin-left: auto; margin-right: auto; width: 75%; max-width: 300px;">
    <thead>
        <tr>
        <th><label id="hSliderLabel" for="hSlider">Hour: 4</label></th>
        <th><label id="mSliderLabel" for="mSlider">Minute: 20</label></th>
        </tr>
    </thead>
    <tbody>
        <tr>
        <td><input id="hSlider" type="range" max="11" value="4"></td>
        <td><input id="mSlider" type="range" max="59" value="20"></td>
        </tr>
    </tbody>
    </table>
</div>

<details markdown="1" class="asciimath2jax_ignore"><summary>Javascript code...</summary>
```javascript
var width;
var height;

function setup() {
  // Work in degrees
  angleMode(DEGREES);

  let demo = document.getElementById("demo");

  width = int(getComputedStyle(demo).width);
  height = int(getComputedStyle(demo).height);

  createCanvas(400, 400);
  
  // Get sliders
  hSlider = document.getElementById("hSlider");
  mSlider = document.getElementById("mSlider");
}

function draw() {
  radius = 0.95 * min(width, height) / 2;
  background(39, 40, 34);
  
  // Draw the clock face
  fill(39, 40, 34);
  stroke(255);
  strokeWeight(2);
  // Set the origin to the centre of the canvas
  translate(width / 2, height / 2);
  // Set the 0 degree mark to the top of the clock
  rotate(-90);
  circle(0, 0, 2 * radius);
  
  // Draw the minute hand
  strokeWeight(3);
  let minutes = int(mSlider.value);
  let a_m = 6 * minutes;
  let x_m = 0.8 * radius * cos(a_m);
  let y_m = 0.8 * radius * sin(a_m);
  line(0, 0, x_m, y_m);
  
  // Hour hand
  strokeWeight(4);
  let hours = int(hSlider.value);
  let a_h = (60 * hours + minutes) / 2;
  let x_h = 0.5 * radius * cos(a_h);
  let y_h = 0.5 * radius * sin(a_h);
  line(0, 0, x_h, y_h);
}
```
</details>

## Exercises
1. Is there another way to derive these formulas using rates of change?
2. Can you find a formula providing the exact times of day where the hour and minute hands overlapping?
3. Can you generalise this idea further by including a seconds hand?
4. In your favourite programming language, write a program that takes the number of seconds since January 1st, 1970 (Unix time) and draws an accurate, realtime, clock.

<script src="https://cdn.jsdelivr.net/npm/p5/lib/p5.min.js"></script>
<script>
var width;
var height;

function setup() {
  // Work in degrees
  angleMode(DEGREES);

  let demo = document.getElementById("demo");

  width = int(getComputedStyle(demo).width);
  height = int(getComputedStyle(demo).height);

  createCanvas(min(400, width), min(400, height));
  windowResized();
  
  // Get sliders
  hSlider = document.getElementById("hSlider");
  mSlider = document.getElementById("mSlider");
}

function windowResized() {
  width = int(getComputedStyle(demo).width);
  height = int(getComputedStyle(demo).height);
  resizeCanvas(min(400, width), min(400, height));
}

function draw() {
  radius = 0.95 * min(width, height) / 2;
  background(39, 40, 34);
  
  // Draw the clock face
  fill(39, 40, 34);
  stroke(255);
  strokeWeight(2);
  // Set the origin to the centre of the canvas
  translate(width / 2, height / 2);
  // Set the 0 degree mark to the top of the clock
  rotate(-90);
  circle(0, 0, 2 * radius);
  
  // Draw the minute hand
  strokeWeight(3);
  let minutes = int(mSlider.value);
  let a_m = 6 * minutes;
  let x_m = 0.8 * radius * cos(a_m);
  let y_m = 0.8 * radius * sin(a_m);
  line(0, 0, x_m, y_m);
  
  // Hour hand
  strokeWeight(4);
  let hours = int(hSlider.value);
  let a_h = (60 * hours + minutes) / 2;
  let x_h = 0.5 * radius * cos(a_h);
  let y_h = 0.5 * radius * sin(a_h);
  line(0, 0, x_h, y_h);
  
  // Label the sliders
  hSliderLabel = document.getElementById("hSliderLabel"); 
  hSliderLabel.textContent = "Hour: " + hSlider.value;

  mSliderLabel = document.getElementById("mSliderLabel");
  mSliderLabel.textContent = "Minute: " + mSlider.value;
}
</script>
