# v0.0.39
- packages hierarchy updated
- prompters renamed
- pipeline in progresss

# v0.0.38
- Fully functionnal pipeline described as a dictionary
- Ability to start and stop a test suite at any point

# v0.0.37
- Small fixes

# v0.0.36 
- Module renamed
- Removed deprecated prompter (see v0.0.33)

# v0.0.35
- PR in progress

# v0.0.34 - May 16th 2024
- bug fixed in question number display in logs (in `LiteLLM.complete`)

# v0.0.33 - May 15th 2024
- removed old Eval prompters `PptrTwoFactsEvalFR` and `PptrSimpleEvalFR` and old Eval generator `TwoFactsEvalGenerator`
- removed old Facts prompter `PptrSimpleFactsFR`
- renamed Answer prompter `PptrBaseAns` to `PptrAnsBase`, Facts prompter `PptrFactsFRv2` to `PptrFactsFR`, Evals prompter `PptrEvalFRv2` to `PptrEvalFR`
- added `save_to...` parameters in `gen_Answers` to ease output files generation
- added a `generate` function in `generators.py` to replace the `gen_Answers`, `gen_Facts` and `gen_Evals` function which where too similar
- added a default `max_tokens` parameters in the `LLM.complete`

# v0.0.32 - May 6th 2024
- generation in async
- logs more precise
- `basic_template.xlsx` updated

# v0.0.31
- added "update_from_spreadsheet"
- updates in config.py regarding column numbers
- renamed Answer Prompters
- minor updates in README.md

# v0.0.30
- tests (folder `tests`) now run `full_test.py` on Windows and Linux (WSL)
- the script `run_tests.py` run the tests on both OS

# v0.0.29
- Update min Python version to 3.9
- Added dependancies
- Uses `Union` typing instead of `|`
- Added a logging instruction in the `main.py` from `base_folder`
- Explicitly sets an extra argument for the Logger (not needed in Python v3.10)
- Added this CHANGELOG.md