---
layout: project
title: This Website
description: This website is a static site generated with Jekyll, hosted on Netlify, aiming to be as easy and lightweight as possible. It is open-source and available on GitHub.
start_date: 2020-08-26T00:00:00.000Z
finished: false
finish_date:
---

{% include math.html %}

This website is a static site generated with [Jekyll](https://jekyllrb.com/), hosted on [Netlify](https://www.netlify.com/), aiming to be as easy, lightweight, and cheap as possible. It is open-source and available on [GitHub](https://github.com/tristanbatchler/tbat.me).

I enjoy having full control over the design and functionality of my website, and being able to host it for free. Although web development is not my main focus, I find it a fun and rewarding hobby. I am always looking for ways to improve the site, so if you have any feedback or suggestions, please let me know! 

## Features

### Code
I include a lot of code snippets in my posts, so it's pretty important they are easy and clear.

```directory
/easy/path/to/code.ml
```
```ocaml
let demo features =
  features
  |> List.append ["Syntax highlighting in code blocks"]
  |> List.append ["Nice directory hint, and a copy button on mouse hover"]
```

### Images
I'll also have a bunch of images. Instead of making sure they're all optimised before-hand, I let Jekyll and Netlify do it fore me with a 
custom image tag:

For example, the following code in a post or project markdown file:

```directory
_projects/this-website.md
```
```liquid
{% raw %}
{% include img.html src="goldie.jpg" %}
*Pretty neat right?*
{% endraw %}
```

will automatically expand to the following HTML:

```html
{% include img.html src="goldie.jpg" %}
<p><em>Pretty neat right?</em></p>
```

{% include img.html src="goldie.jpg" %}
*Pretty neat right?*

### Maths
Every other most might include the odd equation, so I include MathJax on any page that has the `{% raw %}{% include math.html %}{% endraw %}` tag, and I can write LaTeX in my markdown files inline with a double dollar sign.

$$
    x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
$$

This is all just a handy way to include MathJax on pages that need it, without having to load the library on every page of the site.

## Design over the years

The website is always a work in progress, and changes to the design are often driven by my own tastes changing. When I started this site, 
I really liked monokai and serif fonts, but looking back, it gave off a bit of an ameteurish vibe. I gradually moved to a purple theme 
with a more modern font, but also kept to the rounded card-style layout. Eventually I fell back into a darker theme and dropped the round 
borders which I feel is a much more clean, modern design. Who knows, I'l probably going to change it again down the line, but for now, here 
is a nice snapshot of the design evolution.

<div class="project-screenshot-grid">
<div class="project-screenshot-item" markdown="1">
{% include img.html src="website-2023-11-wayback.png" alt="Screenshot of the site from November 2023" %}
*November 2023*
</div>

<div class="project-screenshot-item" markdown="1">
{% include img.html src="website-2024-08-wayback.png" alt="Screenshot of the site from August 2024" %}
*August 2024*
</div>

<div class="project-screenshot-item" markdown="1">
{% include img.html src="website-2025-10-wayback.png" alt="Screenshot of the site from October 2025" %}
*October 2025*
</div>

<div class="project-screenshot-item" markdown="1">
{% include img.html src="website-2026-04-wayback.png" alt="Screenshot of the site from April 2026" %}
*April 2026*
</div>
</div>
