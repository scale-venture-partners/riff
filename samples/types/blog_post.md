# Why our team switched to trunk-based development

We spent two years with long-lived feature branches and a painful merge every release. Last spring we moved to trunk-based development with feature flags. Here is what actually changed.

Merges stopped being events. Because everyone integrates to main daily, conflicts are small and frequent instead of large and rare. The flags let us ship unfinished work safely and turn it on when it is ready.

It was not free. We had to invest in tests we trusted, and in a flag system that did not rot. But six months in, nobody wants to go back.
