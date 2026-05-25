# Issue tracker: GitHub

Issues and PRDs for this repo live in GitHub Issues for `jackj6441/Movie-Recommendation-System`. Use the `gh` CLI for issue operations when working from the local clone.

## Conventions

- Create an issue: `gh issue create --title "..." --body "..."`
- Read an issue: `gh issue view <number> --comments`
- List issues: `gh issue list --state open --json number,title,body,labels,comments`
- Comment on an issue: `gh issue comment <number> --body "..."`
- Apply a label: `gh issue edit <number> --add-label "..."`
- Remove a label: `gh issue edit <number> --remove-label "..."`
- Close an issue: `gh issue close <number> --comment "..."`

Infer the repo from `git remote -v`. `gh` should do this automatically when run inside this clone.

## When a skill says "publish to the issue tracker"

Create a GitHub issue in this repo.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.
