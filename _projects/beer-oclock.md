---
layout: project
title: Beer O'Clock
description: A simple and focused PWA for Queensland beer enjoyers to quickly log beers, estimate BAC, and review session history, with privacy-first defaults.
start_date: 2026-03-01T00:00:00.000Z
finished: false
finish_date:
external_link: https://itsbeeroclock.au
---
<!-- Beer O'Clock is a project I started in March 2026. The goal is simple: if you cannot log a drink in under five seconds, the app is too hard to use.

It is built for real nights out, so the interface stays minimal and every feature is optional by default.

A session starts when the first drink is logged. It ends automatically when estimated BAC returns to zero and no drinks have been logged for at least two hours, then the session is moved to history.

Current version (`v0.1.0`) includes anonymous sessions, a beer catalogue, BAC estimates and graphing, offline-first sync, optional accounts, OTP sign-in, and Cloudflare Turnstile protection.

Tech stack is React + TypeScript on the frontend, Go on AWS Lambda for the backend, and DynamoDB with a single-table design.

Source code: [github.com/tristanbatchler/itsbeeroclock](https://github.com/tristanbatchler/itsbeeroclock) -->

This is my first serious React project. I wanted to make something I would use myself, and something I thought there was an actual need for. 

The result was a hyper-targeted beer consumption tracker for Queensland drinks and sizes. It's pretty inflexible for anything that's not 
specifically Queensland beer, but that's the point. It eliminates the vast majority of friction when it comes to actually keeping track of 
your drinks on a night out, which, as I'm getting older, becomes increasingly important for avoiding hangovers.

{% include grid.html
	folder="projects/beer-oclock/grid"
	columns=4
	captions="Track your session with no hassle|Review your past nights out|Sign up for detailed insights|Australian beers pre-loaded"
%}

## Tech stack
The frontend is built with React and TypeScript, using Vite as the build tool. 

The backend uses a thin Go layer on AWS Lambda, reaching out to DynamoDB for storage with a single-table design.

Authentication is handled with either anonymous sessions, or magic OTP links sent to email or Google Sign-In via Supabase. Cloudflare Turnstile protects the email OTP endpoint from abuse.

The app is a PWA with an offline-first approach, so you can log drinks even without service and they will sync when you're back online.

## AI
AI was used quite a bit in the development of this project. Regardless of my personal opinions, I realised it is important to make sure 
I can manage a project that relies on agentic coding, including managing steering files, documentation, exploring MCP servers and tools, and of course giving decent prompts. I used a combination of Copilot and Amazon Kiro for this project, and I purposefully chose the tech stack 
with this in mind, as I knew these are all extremely well-documented and popular technologies.

That said, I was very conscious that there's the possibility of the agent to eventually steamroll the project into an unmanageable state, so 
I was sure to have at least a basic understanding of everything involved, keep regular audits, and practice good documentation.

Critical parts of the codebase, such as BAC calculations and privacy features, were scrutinised both manually and with other AI tools.

## Future plans
The app is essentially feature-complete for my needs, but I have a few ideas for future improvements:
- Going against the initial philosophy, I'd like an easy way for this to be deployed for other states and countries if others want to do the same thing for their local drinks. This would involve some kind of configuration system, and maybe an admin interface for managing the beer catalogue.
- To sell out and practice my AI and AWS skills, incorporating an opt-in AI insights feature that analyzes your session history and provides personalized recommendations. Privacy would be a top priority, so I would need to carefully look at Bedrock's terms and ensure that any data sent to the AI is properly anonymized and minimal. This may or may not happen.
- Dark mode improvements.