# Clean-prose controls

Every file here must lint to zero with every offline rule enabled, including the off-by-default ones.
`tests/test_false_positives.py` enforces it. A rule that fires on one of these is a bad rule: fix the rule,
not the file. The false-positive budget is what keeps the linter worth running.

Name each file `<doc-type>--<slug>.md`, where `<doc-type>` is one of riff's document types
(`riff --type` takes the same names). The test forces that type, so type-gated rules run the way they
would on a classified document.

Only add prose a person wrote, that the repository may redistribute. Do not add model output, even
edited, and do not paste in someone else's published writing without a licence that allows it.
