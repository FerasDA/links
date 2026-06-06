# Interesting things found on the web

This is my personal link library: useful articles, tools, talks, APIs, and other things I find around the web. It is public so other people can browse it, but link additions are maintained by me.

The site is now an Astro static site. Link data lives in [`data/links.json`](data/links.json), which makes it easier for Hermes and automation scripts to add, enrich, validate, and check links.

## Local development

Install dependencies:

```bash
npm install
```

Validate the link data:

```bash
npm run validate
```

Run tests:

```bash
npm test
```

Build the static site:

```bash
npm run build
```

Run locally:

```bash
npm run dev
```

Then open the local URL Astro prints, usually `http://localhost:4321`.

## Link data structure

Each link has structured metadata:

- `title`
- `url`
- `description`
- `category`
- `tags`
- `type`
- `added`
- `status`

## Direction

The next phases are:

1. Add a Hermes-powered `/addlink` workflow so I can send a link from Slack/email, have Hermes enrich it with category/tags/description, and open a PR.
2. Add a weekly broken-link checker that updates link status and opens a PR for review.
3. Continue refining categories, tags, and descriptions as the library grows.
