# Repository verification

- Read `CONTRIBUTING.md` for standalone-package and generated-guide requirements.
- The full regression suite requires `SKILL_RELEASE_TEST_TEMP` (or `TEMP`) to name an existing absolute scratch directory. On Linux, run `scratch=$(mktemp -d /tmp/ai-film-skills-tests-XXXXXX) && SKILL_RELEASE_TEST_TEMP="$scratch" python -m unittest discover -s tests`.
- Prompt-authoring contract regressions run with `python -m unittest tests.test_prompt_authoring_contract`. These check the written rules, not actual Agent compliance.
- Production regressions run with `python -m unittest tests.test_series_check tests.test_media_qc tests.test_pregeneration_gate tests.test_production_completion_contract`. A synthetic FFmpeg fixture or synthetic A/B scores verify mechanics only; neither is real-film acceptance.
