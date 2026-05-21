# Stack: Ruby

## Stack id

`ruby`

## Manifest fingerprints

- File globs: `**/Gemfile`, `**/Gemfile.lock`, `**/*.gemspec`, `**/Rakefile`, `**/config/routes.rb`, `**/*.rb`, `**/*.erb`
- Content patterns: `source 'https://rubygems.org'` in `Gemfile`; `Rails.application.routes.draw do` in `config/routes.rb`.
- Negative match: `Brewfile` or `cookbook` directories (Chef) are excluded by default.

## Analysis-unit granularity

- **Rails monorepo with engines**: each engine in `engines/<name>/` is one analysis unit.
- **Multi-gem repo**: each `*.gemspec` is one analysis unit.
- **Single Rails app**: the repo root is one unit.
- See [../repo_granularity.md](../repo_granularity.md).

## Parser

- Tree-sitter grammar: `tree-sitter-ruby`.
- Max AST depth: 5.
- ERB templates parsed only to extract action references; the rendered HTML is not analyzed.

## Entry-point kinds detected

| Framework / surface | `entry_point.kind` | Detection signal |
|---|---|---|
| Rails controller action | `http-route` | `config/routes.rb` entries (`resources :x`, `get '<path>', to: 'controller#action'`) + matching action method in `app/controllers/<x>_controller.rb` |
| Rails API controller (`ActionController::API`) | `http-route` | same as above; flagged separately for "no view rendering" semantics |
| Sinatra | `http-route` | `get '<path>' do ... end` / `post '<path>' do ... end` |
| Grape API | `http-route` | `class API < Grape::API ; get '<path>' do ... end ; end` |
| Hanami | `http-route` | `actions/<resource>/<action>.rb` modules |
| Sidekiq worker | `message-consumer` | class `include Sidekiq::Worker` + `def perform(args)` |
| Active Job | `message-consumer` | class extending `ApplicationJob` + `def perform` |
| Whenever cron / `clockwork` | `scheduled-job` | `every 1.hour do ... end` |
| Thor / Rake task | `cli-command` | `task :name do ... end` (Rake); `desc "..."` + `def <name>` (Thor) |
| GraphQL resolver | `graphql-resolver` | `field :name, ...` in `graphql/types/`; `def resolve(**args)` in resolver classes |
| Active Record callback | `db-trigger` | `before_save`, `after_create`, etc., on a model |

## Inputs typing

- Rails: `params` hash is dynamic; Strong Parameters via `params.require(:resource).permit(...)` lists the typed inputs.
- API controllers: `request.body.read` + manual JSON parse → recorded as `unknown` unless a `dry-validation` / `dry-schema` is found.
- Sinatra: `params['name']` → all string-typed.
- Active Model validations (`validates :email, presence: true, format: ...`) captured as `inputs[].validation`.

## Side-effect detection

- Persistence: Active Record `save / save! / update / update! / destroy / create / create!`, Sequel, ROM-rb.
- HTTP clients: `Net::HTTP`, `Faraday`, `HTTParty`, `RestClient`.
- Message publishers: Sidekiq `perform_async`, ActiveJob `perform_later`, Bunny (RabbitMQ) `exchange.publish`, AWS SDK Ruby (`Aws::SQS::Client#send_message`).
- Filesystem and S3: `File.write`, `Aws::S3::Client#put_object`, ActiveStorage `attach`.
- `eval` / `send` with user input → flagged for the error-message leakage / arbitrary-method pattern row.

## Cross-stack bridge hints

- `Net::HTTP` / `Faraday` URL literal → `http-route` resolution.
- AWS SDK calls → `aws-serverless` lookup.
- Sidekiq queue name → cross-unit boundary on the Redis queue identifier.
- See [../cross_stack_bridges.md](../cross_stack_bridges.md).

## Bug-patterns row pointer

See [../bug_patterns.md](../bug_patterns.md) — rows where column `ruby` =
`MUST-if-applicable`. Specifically: N+1 query (`Model.includes` missing),
Strong Parameters bypass via `params.permit!`, Active Record callback
firing on `update_columns` bypassed (callback-skipped path), mass
assignment regression, `where(user_input)` injection manifesting as
functional auth bypass, Sidekiq retry without idempotency leading to
duplicate side effects.

## Empty-input branch

If a unit is detected as `ruby` but **zero** entry points are extracted
(e.g. a gem with only library code), the unit is recorded in
`coverage.md` with skip reason `no-entry-points`. `spec/` and `test/`
directories are auto-excluded with `out-of-scope`.
