# hook-tiered-advisor fixtures

Fixture per `tests/test_hook_session_start_tiered_advisor.py`.

I sotto-repo (`repo-with-fresh-map/`, `repo-with-stale-map/`,
`repo-without-map/`, `repo-with-many-commits/`) sono **placeholder** —
i test costruiscono i repo git con commit backdated runtime in `tmp_path`
(vedi pytest fixtures `repo_with_fresh_map`, `repo_with_stale_map`,
`repo_without_map`, `repo_with_many_commits`).

Motivo: serve `last_mapped` relativo al wall-clock dei test (oggi - 30gg)
e commit con `GIT_AUTHOR_DATE` backdated. Non è riproducibile con file
statici checked-in.

I file `.gitkeep` mantengono le directory tracciate.
