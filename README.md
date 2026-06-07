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

## Adding links

The local add-link helper is the building block for the Hermes `/addlink` workflow. It adds one structured entry to `data/links.json`, rejects duplicate normalized URLs, and leaves new links with `status: "unchecked"` so the checker can verify them later.

Example:

```bash
npm run addlink -- "https://example.com/article" \
  --title "Example Article" \
  --description "A short useful description of the link." \
  --category "Interesting Reads" \
  --tags "interesting-reads,example" \
  --type article
```

Useful options:

- omit `--title` / `--description` to let the helper try page metadata first
- pass `--no-fetch` to skip network metadata lookup
- pass `--dry-run` to validate without writing

A Hermes-assisted add should:

1. Create a branch.
2. Fetch/enrich the URL metadata and choose category, tags, type, and description.
3. Run `npm run addlink -- <url> ...`.
4. Run `npm run validate`, `npm test`, and `npm run build`.
5. Commit, push, and open a PR for review.

## Normalizing taxonomy

The normalize helper keeps category tags consistent and trims simple text whitespace:

```bash
npm run normalize
```

Use `--dry-run` to preview how many links would change without writing:

```bash
npm run normalize -- --dry-run
```

## Checking links

The link checker updates reviewable status metadata for existing links:

```bash
npm run checklinks
```

Useful options:

- pass `--dry-run` to report results without writing
- pass `--limit N` to check only the first N links while testing
- pass `--timeout 15` to adjust the per-link request timeout

The scheduled GitHub Action runs weekly and opens a PR if `data/links.json` changes. It updates fields such as:

- `status`: `ok`, `redirected`, `broken`, or `unknown`
- `last_checked`
- `redirect_url` for redirects
- `check_error` for broken or unknown checks

The checker never deletes links automatically.

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
