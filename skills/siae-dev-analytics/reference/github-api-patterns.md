# GitHub API Patterns — siae-dev-analytics

Query GraphQL usate da `collect_github.py`.

## Query principale

```graphql
query($owner: String!, $name: String!, $since: DateTime!) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: MERGED, first: 100) {
      nodes { number author{login} createdAt mergedAt
        commits(first:1) { nodes { commit { committedDate } } }
        reviews(first:50) { nodes { createdAt comments { totalCount } } }
        files(first:100) { nodes { path } }
        body
      }
    }
    defaultBranchRef {
      target { ... on Commit {
        history(since:$since, first:100) {
          nodes { oid author{user{login}} committedDate message }
        }
      }}
    }
    refs(refPrefix:"refs/tags/", first:50) {
      nodes { name target{oid} }
    }
  }
}
```

## Invocazione via gh CLI

```bash
gh graphql -f query="$Q" -F owner=itsiae -F name=catalogo-service -F since=2026-01-01T00:00:00Z
```

## Rate limit management

- Cache locale `.cache/github/<hash>.json` deterministica
- Backoff esponenziale su "rate limit exceeded" (60s, 120s, 240s)
- Retry max 3 volte, poi RuntimeError

## Paginazione

v1 usa `first: 100`. Per repo > 100 PR nella finestra, estendere con `after` cursor.
