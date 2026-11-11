"""Jev (semantic) rules — the bulk of the catalog.

Every writing tell that is a judgment lives here as one Noul question asked about a single prose
block. Instructions are phrased so the returned probability is the probability the tell IS PRESENT
(Jev performs worse when true maps to "no"). Where two rules are easy to confuse, instructions carry
a `not_for` field so the model can separate them.

This is deliberately Jev-first: pattern-and-phrase matching misses paraphrases and fires on
look-alikes, so anything that depends on meaning or context is a question here, not a regex. Only
things Jev cannot do stay in code (see static_rules.py): exact glyphs it never sees, cross-block
duplicate detection, and arithmetic metrics.

Codes: JEV0xx structure/composition, JEV1xx tone/voice, JEV2xx substance, JEV3xx word & phrase
choice, JEV4xx clarity & grammar (Williams), JEV6xx type-specific, JEV7xx narrative -- rules that
judge a title, a whole section, or the document's outline rather than one paragraph.
"""

from __future__ import annotations

from riff.rules.base import jev_rule

T = "tropes.fyi"
W = "Williams, Style: Lessons in Clarity and Grace"
E = "Strunk & White, The Elements of Style"


def D(entry: int | str) -> str:  # noqa: N802 - reads like the other source constants at the call site
    """The declauding register (Austegard, github.com/oaustegard/claude-skills, MIT), by entry number."""
    return f"declauding register, entry {entry} (Austegard)"


# The cluster of GitHub PR descriptions that grew from 0.70% of early 2025 to 39.5% of August 2026 (Louis
# Abraham's load-bearing corpus, 461k descriptions), as analysed in declauding's references/corpus.md.
CORPUS = "Abraham, load-bearing PR-description corpus, via declauding references/corpus.md"
# Clark, Martin and Mahowald on syntactic compression in model output.
COMPRESSION = "Clark, Martin & Mahowald, arXiv 2610.29162, via declauding entries 53-56"

# ---------------------------------------------------------------- structure / composition (JEV0xx)

jev_rule(
    "JEV001", "preamble", "Announces what it is about to say instead of saying it",
    category="Composition", source=T, threshold=0.65, skip_for=("documentation", "presentation"),
    explanation="Opening that sets up the answer instead of being the answer (\"Two constraints shape the design\").",
    examples=("Two constraints shape the design.", "Before diving in, let me set up what follows."),
    question={
        "question": "Does this passage mainly announce, preface, or set up what it is about to say, instead of "
        "directly saying it?",
        "includes": "Structural announcers naming the count or shape of what follows, throat-clearing frames, "
        "and restating the prompt before answering.",
        "not_for": "A passage that states its actual point directly, even if it opens with a topic sentence.",
    },
)

jev_rule(
    "JEV002", "reasoning-leak", "Narrates its own writing or thinking process",
    category="Composition", source=T, threshold=0.7,
    explanation="Chain-of-thought residue: narrating what the text or author is doing, deciding, or about to do.",
    examples=("I want to be exact about my own role here.", "What that changes is worth being precise about."),
    question={
        "question": "Does this passage narrate the act of writing or the author's own deliberation about how to "
        "write it, rather than delivering the content?",
        "not_for": "First-person narration of real events, decisions, or opinions that are themselves the subject "
        "(for example a retrospective reflecting on past predictions).",
    },
)

jev_rule(
    "JEV003", "premise-stacking", "Makes its point only after a wall of its own evidence",
    category="Composition", source=T, threshold=0.7, default=False,
    explanation="A point preceded by a paragraph of its own evidence, so it is over-made before it lands.",
    question={
        "question": "Does this passage pile up supporting evidence or context before finally stating the point it "
        "was building toward, so the point is over-justified by the time it arrives?",
        "not_for": "A short claim followed by one supporting reason.",
    },
)

jev_rule(
    "JEV004", "tie-back", "Closes by restating the answer and looping back to the question",
    category="Composition", source=T, threshold=0.65,
    explanation="Bolting a summary of itself back onto the ask (\"So, to answer your question, X does Y\").",
    examples=("So, to answer your question: yes.", "In short, this gives you everything you need."),
    question={
        "question": "Does this passage restate its own conclusion and loop back to the original question or topic as "
        "a wrap-up of what was already said?",
        "not_for": "A genuinely new concluding point that adds information.",
    },
)

jev_rule(
    "JEV005", "belaboring", "Defends a minor point against an objection nobody raised",
    category="Composition", source=T, threshold=0.7, default=False,
    explanation="Stating a small, uncontroversial point just to justify it as if anticipating an objection.",
    question={
        "question": "Does this passage over-explain or defend a minor, uncontroversial point as if anticipating an "
        "objection that nobody was likely to raise?",
    },
)

jev_rule(
    "JEV006", "signposted-conclusion", "Explicitly announces that it is concluding",
    category="Composition", source=T, threshold=0.7,
    explanation="\"In conclusion\", \"to sum up\", \"in summary\" — competent endings don't need to announce themselves.",
    examples=("In conclusion, the future depends on trust.", "To sum up, we've covered three themes."),
    question={
        "question": "Does this passage explicitly announce that it is summarizing or concluding (with a phrase such "
        "as 'in conclusion', 'to sum up', 'in summary', or an equivalent), rather than simply ending?",
    },
)

jev_rule(
    "JEV007", "fractal-summary", "Restates itself at the start or end of a section",
    category="Composition", source=T, threshold=0.7, default=False,
    explanation="\"What I'll tell you / what I'm telling you / what I told you\" applied at every level.",
    question={
        "question": "Does this passage preview what a section will cover or recap what it already covered, adding a "
        "layer of self-summary rather than new content?",
    },
)

jev_rule(
    "JEV008", "enumerated-prose", "A listicle disguised as prose (\"The first… The second…\")",
    category="Paragraph Structure", source=T, threshold=0.7,
    explanation="Numbered points wrapped in paragraphs opening with ordinals, to hide that it is a list.",
    examples=("The first wall is… The second wall is… The third wall is…",),
    question={
        "question": "Does this passage deliver a sequence of points as prose that each open with an ordinal ('The "
        "first…', 'The second…', 'Third,…'), reading like a numbered list rewritten as paragraphs?",
    },
)

jev_rule(
    "JEV009", "never-ending-conclusion", "The ending stacks clause after clause instead of stopping",
    category="Composition", source=T, threshold=0.7, default=False,
    explanation="Reluctant to stop: the close piles on qualifications and extra clauses rather than landing one point.",
    question={
        "question": "Does this passage's closing stack clause after clause or qualification after qualification, as "
        "if reluctant to stop, instead of landing a single clear final point?",
    },
)

jev_rule(
    "JEV010", "formulaic-structure", "Follows a formulaic template, hitting every expected beat in order",
    category="Composition", source=T, threshold=0.65, scope="document", skip_for=("presentation",),
    explanation="Whole-message tell: an AI-generated piece that marches through the canonical beats of its genre "
    "(for outreach: intro, a flattering observation, a thesis, boilerplate about the sender, a soft ask) in order. "
    "Asked once over the whole document, since the tell is the overall shape, not any one paragraph.",
    examples=("A cold email that introduces, flatters, pitches a thesis, recites who-we-are, then asks for a chat.",),
    question={
        "question": "Does this whole piece read as a formulaic, AI-generated message that marches through the "
        "standard beats of its genre in the expected order, rather than being shaped by what it actually needs to say?",
        "not_for": "A piece with a natural, purpose-driven structure, even if it is conventional.",
    },
)

jev_rule(
    "JEV011", "revision-artifact", "Leaves a note about its own edits that the final reader doesn't need",
    category="Composition", source="Observed in AI-edited slides and docs", threshold=0.7,
    skip_for=("release_notes", "notes"),
    explanation="Editing-session residue: a revision asked for in chat leaks into the document as a footnote, "
    "badge, or aside about what changed (\"+2 companies added\"), so notes accumulate that only the person who "
    "requested the edit understands. Say the content, not the fact that it was added or changed.",
    examples=("Revenue by segment (updated to include the two new companies)", "Note: revised per your feedback."),
    question={
        "question": "Does this passage mention that it was edited, updated, revised, or extended (for example "
        "'updated to include', '+2 added', 'per your feedback', 'v2', 'revised', 'previously said X'), such that the "
        "note only makes sense to someone who watched the document being changed?",
        "includes": "Parenthetical or footnote badges about additions or removals, change-tracking asides, and "
        "references to earlier drafts or to a request to change the document.",
        "not_for": "Content that is about change itself (a changelog, a dated 'last updated' stamp, a discussion of "
        "how a plan evolved, or a real correction the reader must know about).",
    },
)

jev_rule(
    "JEV013", "uniform-front-loading", "Every paragraph opens by stating its point, with no digression or build-up",
    category="Composition", source="Corpus calibration; NN/g front-loading (the inverse is the human norm)",
    threshold=0.65, share_below=0.10, applies_to=("blog_post", "essay", "article"),
    explanation="Human prose wanders: roughly a quarter of paragraphs set up, digress, or reach their point late. "
    "AI drafts state the point in the first sentence of nearly every paragraph. Asked of every paragraph; the "
    "document is flagged once when 10% or fewer paragraphs open with setup. Gated to blog posts, essays and "
    "articles, where front-loading everywhere is a tell; in memos, reports and docs it is the advice.",
    examples=("Every paragraph opens with its topic sentence and spends the rest supporting it.",),
    question={
        "question": "Does this paragraph open with background, setup or an aside, with its main point arriving only "
        "in a later sentence, instead of stating its point in the first sentence?",
    },
)

# Rules from the declauding register below are off by default until they are probed against the live model
# (CONTRIBUTING, "Adding a Jev rule"). Each question carries the register's "earned when" case as not_for,
# since every shape it names sometimes carries a real claim.

jev_rule(
    "JEV012", "no-discernible-point", "No single point a reader could state after reading it",
    category="Composition",
    source="declauding, workflow step 1a (Austegard); replies to Vinitsky's 2026-11-09 post on editing LLM text",
    threshold=0.7, scope="document", default=False,
    skip_for=("notes", "sms", "chat_message", "poem", "script", "resume", "presentation", "release_notes"),
    explanation="Every sentence can be locally fine while the piece says little: readers of model drafts report "
    "reaching the end of a page and not knowing what it said. Ask whether a reader could state, in one sentence of "
    "their own, what the piece wants them to come away knowing, and whether most of its length bears on that. "
    "Sentence-level rules cannot see this; the fix is to write the point first and rebuild from it, keeping only "
    "what supports it. Asked once over the whole document.",
    examples=("Four paragraphs on 'the evolving landscape of observability' that never say what to do or what changed.",),
    question={
        "question": "After reading this whole piece, would a reader be unable to say in one sentence what it wants "
        "them to know or do, because it has no clear main point, or because most of its length is spent on "
        "material that does not bear on that point?",
        "not_for": "A piece with a clear point, even if it is long, digressive in places, or the point is stated "
        "late; reference material (an API list, a glossary, a table) whose job is to be looked up rather than to "
        "argue; and a piece that covers several items the reader asked for.",
    },
)

jev_rule(
    "JEV014", "contents-list-standfirst", "Opens with a contents list shaped as a sentence ('X, plus Y')",
    category="Composition", source=D(42), threshold=0.72, scope="document", default=False,
    skip_for=("presentation", "notes", "sms", "chat_message", "email", "letter"),
    explanation="A subtitle or first line built as '<noun phrase>, plus <noun phrase>' -- 'The parameter surface, "
    "plus the behavior the schema leaves out' -- is a table of contents wearing a sentence. The second half is "
    "usually a coy reduced relative that claims value without naming any. Say what the page contains, or drop "
    "the subtitle.",
    examples=("The create_session parameter surface, plus the behavior the schema leaves out.",
              "Our migration, and the three things you need to know."),
    question={
        "question": "Does this piece open (its first line, subtitle or standfirst) with a list of its contents "
        "phrased as a sentence -- a noun phrase joined by 'plus' or 'and' to a teasing second noun phrase such as "
        "'the part the docs skip' or 'the N things you need to know' -- instead of saying what it shows?",
        "not_for": "An opening that states a fact, a finding or what the page contains in plain terms; an "
        "ordinary title; and a first line that is the start of the argument itself.",
    },
)

# ---------------------------------------------------------------- tone / voice (JEV1xx)

jev_rule(
    "JEV101", "stakes-inflation", "Inflates ordinary stakes to world-historical significance",
    category="Tone", source=T, threshold=0.65,
    explanation="Everything is the most important thing ever; a post about API pricing becomes about civilization.",
    examples=("This will fundamentally reshape how we think about everything.",),
    question={
        "question": "Does this passage inflate the importance or stakes of its subject to a grand, sweeping, or "
        "world-changing level out of proportion to what is actually being discussed?",
    },
)

jev_rule(
    "JEV102", "invented-concept-label", "Coins an abstract term as if it were established",
    category="Tone", source=T, threshold=0.65,
    explanation="Compound problem-labels (paradox, trap, creep) used as if rigorously defined. Names a thing, skips the argument.",
    examples=("the supervision paradox", "the acceleration trap", "workload creep"),
    question={
        "question": "Does this passage coin or use an abstract compound label (a named 'paradox', 'trap', 'creep', "
        "'divide', 'inversion', and the like) as if it were an established, defined term, without defining it?",
    },
)

jev_rule(
    "JEV103", "quotable-bait", "A standalone quotable line that carries no real information",
    category="Tone", source=T, threshold=0.72,
    explanation="A line built to be pulled out and read alone as wisdom, but says nothing concrete.",
    examples=("Every metric that rewards volume punishes leverage.",),
    question={
        "question": "Is this passage a self-contained, aphoristic line engineered to sound quotable or profound while "
        "conveying little or no concrete information?",
        "not_for": "A concrete factual claim, even if concise.",
    },
)

jev_rule(
    "JEV104", "forced-figurative", "A simile or metaphor reached for to sound clever, not to clarify",
    category="Tone", source=T, threshold=0.72, default=False,
    explanation="A forced figure of speech that nobody would actually use, added for cleverness.",
    question={
        "question": "Does this passage use a simile or metaphor that is strained or ornamental, reached for to sound "
        "clever rather than to make the point clearer?",
        "not_for": "A plain, apt comparison that genuinely aids understanding.",
    },
)

jev_rule(
    "JEV105", "false-vulnerability", "Performative self-awareness or risk-free 'honesty'",
    category="Tone", source=T, threshold=0.72, default=False,
    explanation="Simulated candor that reads as performance; polished admissions that cost nothing.",
    question={
        "question": "Does this passage perform self-awareness, confession, or vulnerability in a polished, risk-free "
        "way that feels staged rather than genuinely candid?",
    },
)

jev_rule(
    "JEV106", "collaborative-we", "Drifts into an unearned collective 'we'",
    category="Tone", source=T, threshold=0.75, default=False,
    explanation="Switching a single author's voice into 'we'/'us', signalling a loss of personal voice.",
    question={
        "question": "Does this passage use a collective 'we', 'us', or 'our' for what is really a single author's "
        "voice, in a way that reads as generic corporate phrasing?",
        "not_for": "Text where a real group or team is genuinely the actor.",
    },
)

jev_rule(
    "JEV107", "rule-of-three", "Stacks parallel triples (tricolons) back to back",
    category="Sentence Structure", source=T, threshold=0.7, default=False,
    explanation="A single tricolon is elegant; three back-to-back rule-of-three structures are a pattern failure.",
    examples=("Products impress people; platforms empower them. Products solve problems; platforms create worlds…",),
    question={
        "question": "Does this passage stack multiple rule-of-three (tricolon) or parallel-triple structures back to "
        "back, so the parallelism itself becomes a repetitive pattern?",
        "not_for": "A single tricolon or one list of three, which is normal and often good writing.",
    },
)

jev_rule(
    "JEV108", "false-suspense", "A \"here's the kicker\" transition promising a revelation",
    category="Tone", source=T, threshold=0.68,
    explanation="Manufactured drama (\"here's the thing\", \"but here's the catch\") before an unremarkable point.",
    examples=("Here's the thing about AI adoption.", "But here's the catch."),
    question={
        "question": "Does this passage use a suspense-building transition that promises a revelation or hidden insight "
        "(like 'here's the thing', 'here's the kicker', 'but here's the catch') before making its point?",
    },
)

jev_rule(
    "JEV109", "pedagogical-voice", "A hand-holding, teacher-to-student voice",
    category="Tone", source=T, threshold=0.68,
    explanation="Talks down to the reader (\"let's break this down\", \"think of it as…\") even for expert audiences.",
    examples=("Let's break this down step by step.", "Think of it like a highway for data."),
    question={
        "question": "Does this passage adopt a hand-holding, teacher-to-student voice — walking the reader through, "
        "offering a simplifying analogy, or otherwise talking down — rather than addressing them as a peer?",
    },
)

jev_rule(
    "JEV111", "formulaic-close", "A canned, low-pressure sign-off",
    category="Tone", source=T, threshold=0.68, skip_for=("presentation",),
    explanation="The interchangeable outreach closer: 'no agenda', 'no pressure', 'happy to hop on a call', "
    "'whatever works for you', 'let me know if that works'.",
    examples=("No agenda beyond getting acquainted.", "Happy to do a call too if that's easier."),
    question={
        "question": "Does this end with a canned, low-pressure sign-off of the kind found in template outreach "
        "('no agenda', 'no pressure', 'happy to hop on a call', 'whatever works for you', 'let me know')?",
    },
)

jev_rule(
    "JEV112", "misplaced-greeting", "A personal greeting or sign-off where the format doesn't call for one",
    category="Composition", source=T, threshold=0.7, scope="document", skip_for=("email", "letter", "presentation"),
    explanation="A greeting ('Hi Sam,') or sign-off ('Thanks, — Alex') is expected in an email or letter, "
    "but out of place in a memo, report, essay, SMS, or documentation. This rule skips email and letter; "
    "for any other type (or an unresolved one) it flags the greeting.",
    examples=("Hi team, — opening a memo", "Thanks! — closing a report"),
    question={
        "question": "Does this open with a personal greeting addressed to someone, or close with a letter/email "
        "style sign-off (a valediction like 'Thanks', 'Best', 'Regards' followed by a name)?",
        "not_for": "A title, a subject line, or body text that merely mentions a name.",
    },
)

jev_rule(
    "JEV110", "futurist-invitation", "\"Imagine a world where…\" salesmanship",
    category="Tone", source=T, threshold=0.72, default=False,
    explanation="The classic 'Imagine…' invitation followed by a list of wonders if the reader agrees.",
    question={
        "question": "Does this passage invite the reader to 'imagine' or 'picture' a hypothetical future as a way of "
        "selling an argument, rather than stating it?",
    },
)

jev_rule(
    "JEV113", "stranded-auxiliary", "A reversal that lands on a bare auxiliary ('The tool died; the data didn't.')",
    category="Sentence Structure", source=D(49), threshold=0.72, default=False,
    explanation="The auxiliary carries the reversal and the verb is elided, so the clause lands as a beat rather "
    "than a fact: 'The tool died; the data didn't.' Say what the second half claims ('The rows already written "
    "are still in the bucket').",
    examples=("The tool died; the data didn't.", "Reading mostly passed. Writing didn't.", "Maybe it wouldn't have."),
    question={
        "question": "Does a clause or sentence here end on a bare auxiliary verb ('didn't', 'wasn't', 'won't', "
        "'hasn't') to deliver a reversal as a dramatic beat, with the actual claim of that half left unstated?",
        "not_for": "Ordinary ellipsis where the elided verb was just used and the contrast rides in the same "
        "breath; and a contrast where both halves carry their measured facts ('reads passed on all 12 shards, "
        "writes on none').",
    },
)

jev_rule(
    "JEV114", "welded-epigram", "A factual clause welded to a second clause restating it as a maxim",
    category="Sentence Structure", source=D(39), threshold=0.72, default=False,
    explanation="A clause that says what happens is joined by 'and' or 'so' to one that restates it as a general "
    "truth: 'Entries the caller does not hold are dropped, so a child never carries a grant its parent lacks.' The "
    "second clause has no concrete noun, would be true of any system, and drops the conditions that made the "
    "first precise. It hides mid-sentence, so a check on paragraph closers misses it. Keep the first clause.",
    examples=("Entries the caller does not hold are dropped, so a child never carries a grant its parent lacks.",
              "The rest of the surface depends on this parameter, and the failure it prevents is silent."),
    question={
        "question": "Does a sentence here state a specific fact and then attach, with 'and' or 'so', a second "
        "clause that restates that fact as a general, quotable truth with no new concrete information?",
        "not_for": "A second clause that adds a new concrete consequence the reader has not seen (a number, a "
        "named effect, what the user must do); and a whole standalone aphoristic sentence (JEV103).",
    },
)

jev_rule(
    "JEV115", "spec-ese", "Reads like a standards document instead of a person explaining",
    category="Tone", source=D(40), threshold=0.72, default=False, skip_for=("academic_paper",),
    explanation="A demonstrative subject where 'it' would do ('That child holds no repository'), reflexive "
    "emphatics ('does not itself hold'), latinate state verbs for a program doing nothing ('idles', 'holds', "
    "'carries', 'awaits'), and the actor displaced into a subordinate clause. The formality signals precision "
    "without adding any. Use 'it', the verb you would say aloud, and name the reader where they are the actor.",
    examples=("That child holds no repository and awaits input.", "Omit it and the child idles awaiting input."),
    question={
        "question": "Is this passage written in the stiff register of a standards document -- demonstrative "
        "subjects like 'That process' where 'it' would do, reflexive emphatics like 'does not itself', or formal "
        "state verbs like 'holds', 'carries', 'idles', 'awaits' for a program simply doing nothing -- rather than "
        "the way a person would explain it aloud?",
        "not_for": "Terms that are the system's own documented vocabulary (a state literally named 'waiting' or "
        "'held'), quoted specification text, and normative language in an actual spec or RFC.",
    },
)

# ---------------------------------------------------------------- substance (JEV2xx)

jev_rule(
    "JEV201", "one-point-dilution", "Restates one idea several ways without adding anything",
    category="Composition", source=T, threshold=0.7, default=False,
    explanation="Padding one thesis to feel comprehensive by rephrasing it with new metaphors and framings.",
    question={
        "question": "Does this passage restate one idea multiple times with different wording or framing, without "
        "adding new information each time?",
    },
)

jev_rule(
    "JEV202", "superficial-analysis", "Attaches hollow significance to a mundane fact",
    category="Substance", source=T, threshold=0.68,
    explanation="Trailing clauses asserting broader meaning ('highlighting its importance') while saying nothing.",
    examples=("contributing to the region's rich cultural heritage",),
    question={
        "question": "Does this passage tack on a claim of broader significance, legacy, or importance to a mundane "
        "fact, adding no real information (for example a trailing 'highlighting/underscoring/reflecting' clause)?",
    },
)

jev_rule(
    "JEV203", "despite-challenges", "Raises a problem only to immediately wave it away",
    category="Composition", source=T, threshold=0.72, default=False,
    explanation="The rigid 'Despite its [good things], [subject] faces challenges … Despite these, it thrives' formula.",
    question={
        "question": "Does this passage raise a problem or challenge only to immediately dismiss it and pivot back to "
        "an optimistic conclusion, following a formulaic 'despite the challenges' shape?",
    },
)

jev_rule(
    "JEV204", "vague-attribution", "Attributes a claim to an unnamed authority",
    category="Substance", source=T, threshold=0.68,
    explanation="\"Experts argue\", \"studies show\", \"observers note\" — borrowed authority with no named source.",
    examples=("Experts argue this has significant drawbacks.", "Industry reports suggest adoption is accelerating."),
    question={
        "question": "Does this passage attribute a claim to an unnamed or vague authority ('experts', 'studies', "
        "'observers', 'reports', 'many believe') instead of naming a specific source?",
        "not_for": "A claim attributed to a named person, organization, or specific cited work.",
    },
)

jev_rule(
    "JEV205", "appeal-to-familiarity", "Asserts canonical status without evidence",
    category="Tone", source=T, threshold=0.7, default=False,
    explanation="\"A classic\", \"famously\", \"as we all know\" — borrowing consensus from the reader's supposed knowledge.",
    question={
        "question": "Does this passage assert that something is well-known, canonical, or famous ('a classic', "
        "'famously', 'notoriously', 'as we all know') to lend it weight, without giving evidence?",
    },
)

jev_rule(
    "JEV207", "generic-boilerplate", "Interchangeable boilerplate that could describe almost anyone",
    category="Substance", source=T, threshold=0.75,
    skip_for=("notes", "sms", "chat_message", "script"),
    explanation="Language so generic it would fit any organization, product, or person in the category, carrying no "
    "distinguishing specifics.",
    examples=("We partner with our customers to drive outcomes and deliver value at every stage of the journey.",),
    question={
        "question": "Is this passage interchangeable boilerplate — phrasing so generic it could describe almost any "
        "organization, product, or person of its kind, without any distinguishing specifics?",
        "not_for": "A conventional greeting, sign-off, or closing; a short functional or transactional line "
        "(an instruction, a cross-reference, a spec); or a concrete, specific description.",
    },
)

jev_rule(
    "JEV208", "faux-personalization", "Sprinkles specifics to seem researched without genuine detail",
    category="Substance", source=T, threshold=0.7, default=False,
    explanation="Outreach tell: name-dropping specific people, companies, or facts to appear personally researched, "
    "while the personalization stays shallow or decorative.",
    examples=("I saw you were at [Company] back in the day, so the name probably rings a bell.",),
    question={
        "question": "Does this drop specific names, companies, or facts to appear personally researched, while the "
        "personalization stays shallow or decorative rather than reflecting genuine specific knowledge?",
    },
)

jev_rule(
    "JEV206", "rapid-fire-analogies", "Lists historical companies or shifts to build false authority",
    category="Composition", source=T, threshold=0.72, default=False,
    explanation="Rapid-fire naming of past companies or tech revolutions to borrow their weight.",
    examples=("Apple didn't build Uber. Facebook didn't build Spotify. Stripe didn't build Shopify.",),
    question={
        "question": "Does this passage rattle off a list of historical companies, products, or technological shifts "
        "to build authority or draw a sweeping parallel, rather than to make a specific point?",
    },
)

jev_rule(
    "JEV209", "exhaustive-negation", "An absolute negative stands in for the evidence ('nothing else could cause it')",
    category="Substance", source=f"{D(47)}; {CORPUS}", threshold=0.72, default=False,
    explanation="'Nothing in the fit varies with time', 'there is nowhere else for it to be', 'no path reaches "
    "it'. A universal negative is the strongest claim and the most expensive to establish, so it is the cheapest "
    "to assert; it is a claim about a search the reader never sees. 'nobody', 'nowhere' and 'nothing' are all in "
    "the corpus cluster's top twenty-five words. State the scope actually checked.",
    examples=("Nothing in the fit varies with time.", "There is nowhere else for the rise to be."),
    question={
        "question": "Does this passage rest a claim on an absolute negative -- 'nothing', 'nobody', 'nowhere', "
        "'no path', 'never' -- asserted as the finding itself, without naming the bounded set or the mechanism "
        "that was checked to establish it?",
        "not_for": "A negative over a set the reader can see ('none of the 46 chunks exceeds 0.57%'); a negative "
        "that follows from a stated exhaustive mechanism ('the enum has three members and the switch covers all "
        "three'); and an ordinary factual denial ('the API does not return a cursor').",
    },
)

jev_rule(
    "JEV210", "totalizing-designation", "Claims a total where a part was shown ('that's the whole point')",
    category="Substance", source=D(51), threshold=0.72, default=False,
    explanation="'That's the whole point', 'the entire business model is X', 'the only marketing I trust'. The "
    "total claims the rest is decoration, and 'the only X' ranks a field whose other members are never named, "
    "so there is nothing to check or disagree with. State the part, and let it be a part.",
    examples=("That's the whole point of the format.", "Changelogs are the only release notes I trust."),
    question={
        "question": "Does this passage declare something 'the whole point', 'the entire X', 'the only thing that "
        "matters' or 'the only X I trust', claiming a total or a ranking over an unnamed set instead of stating "
        "the specific part that was shown?",
        "not_for": "A real count of one over a named set ('the only one of the six runs that finished').",
    },
)

jev_rule(
    "JEV211", "retroactive-significance", "Grades a passage the reader already read ('that's why X mattered')",
    category="Substance", source=D(50), threshold=0.72, default=False,
    explanation="'That's why being able to open the environment mattered.' Telling the reader which earlier "
    "sentence mattered admits the earlier sentence did not carry it. If it did not, fix the earlier passage; "
    "otherwise cut the grade.",
    examples=("That's why being able to open the environment mattered.", "This is why keeping every transcript counted."),
    question={
        "question": "Does this passage look back and tell the reader that something already described 'mattered', "
        "'counted' or was 'why' something worked, grading earlier content rather than adding new information?",
        "not_for": "A 'which is why' that introduces a new consequence the reader has not yet seen.",
    },
)

jev_rule(
    "JEV212", "speculative-gap-filling", "Writes about a missing source, then fills the gap with a stock guess",
    category="Substance", source=D(33), threshold=0.7, default=False,
    explanation="'While specific details are limited', 'based on available information', 'maintains a low "
    "profile', 'likely grew up in', 'as of my last update'. Two tells with one cause: the writer cannot find a "
    "source, says so in a sentence about the search rather than the subject, then supplies an unsourced guess. "
    "Say what is not known, or cut it; never dress the guess as fact.",
    examples=("Information about her early life is not publicly available, suggesting she maintains a low profile.",
              "She likely grew up in a middle-class household."),
    question={
        "question": "Does this passage comment on the lack of available information or sources ('details are "
        "limited', 'not publicly available', 'based on available information', 'as of my last update') or fill "
        "such a gap with a stock, unsourced guess ('likely grew up', 'it is believed that', 'maintains a low "
        "profile')?",
        "not_for": "A plain, specific statement of what a named source does or does not cover ('the 2019 filing "
        "does not list her salary'), and real uncertainty stated with its reason.",
    },
)

# ---------------------------------------------------------------- word & phrase choice (JEV3xx)

jev_rule(
    "JEV301", "ai-vocabulary", "Overused AI filler vocabulary used as filler",
    category="Word Choice", source=T, threshold=0.65,
    explanation="delve, leverage, utilize, robust, seamless, harness — flagged only when used as empty inflation.",
    examples=("Let's delve into this robust framework.", "We harness synergies to unlock value."),
    question={
        "question": "Does this passage use inflated, overused AI-flavored vocabulary (such as 'delve', 'leverage', "
        "'utilize', 'robust', 'seamless', 'harness', 'streamline') where a plainer word would do?",
        "not_for": "A flagged word used as a precise, concrete term the passage is actually about (for example "
        "'harness' in a text whose subject is an agent harness).",
    },
)

jev_rule(
    "JEV302", "magic-adverb", "An adverb inflating significance ('quietly', 'fundamentally')",
    category="Word Choice", source=T, threshold=0.68,
    explanation="'quietly', 'deeply', 'fundamentally', 'remarkably' used to make the mundane feel significant.",
    examples=("quietly orchestrating everything", "this will fundamentally change the field"),
    question={
        "question": "Does this passage lean on an adverb like 'quietly', 'deeply', 'fundamentally', 'remarkably', or "
        "'arguably' to manufacture a sense of significance that the sentence would not otherwise carry?",
        "not_for": "An adverb doing real, literal work (for example 'the server quietly logs errors' meaning without noise).",
    },
)

jev_rule(
    "JEV303", "ornate-noun", "An ornate or grandiose noun where a plain word fits",
    category="Word Choice", source=T, threshold=0.7,
    explanation="'tapestry', 'landscape', 'paradigm', 'ecosystem', 'realm' used decoratively.",
    examples=("the rich tapestry of human experience", "navigating the complex landscape of AI"),
    question={
        "question": "Does this passage use an ornate or grandiose noun ('tapestry', 'landscape', 'paradigm', "
        "'ecosystem', 'realm', 'cornerstone') decoratively where a plain word would do?",
        "not_for": "A word used in its literal, technical sense (for example 'landscape' meaning physical terrain).",
    },
)

jev_rule(
    "JEV304", "promotional-language", "Reads like marketing copy rather than description",
    category="Tone", source=T, threshold=0.68,
    skip_for=("marketing_copy", "product_description", "social_post", "press_release"),
    explanation="Selling the subject instead of describing it: 'all-in-one', 'unprecedented', 'seamless experience'.",
    examples=("an all-in-one solution that unlocks unprecedented productivity",),
    question={
        "question": "Does this passage read like marketing or brochure copy — selling or hyping the subject with "
        "superlatives — rather than plainly describing it?",
        "not_for": "Neutral factual description, even of a product's real capabilities.",
    },
)

jev_rule(
    "JEV305", "empty-transition", "A filler transition that connects nothing",
    category="Sentence Structure", source=T, threshold=0.7, default=False,
    explanation="'It's worth noting', 'importantly', 'interestingly' — signals a point without earning the connection.",
    question={
        "question": "Does this passage open with a filler transition ('it's worth noting', 'importantly', "
        "'interestingly', 'notably') that adds emphasis or connection without any real logical link?",
    },
)

jev_rule(
    "JEV306", "serves-as-dodge", "A pompous copula ('serves as', 'stands as') instead of 'is'",
    category="Word Choice", source=T, threshold=0.7, default=False,
    explanation="Avoiding plain 'is'/'are' with 'serves as', 'stands as', 'represents', 'marks'.",
    question={
        "question": "Does this passage replace a plain 'is' or 'are' with a pompous alternative such as 'serves as', "
        "'stands as', 'represents', or 'marks', where the simple verb would read better?",
    },
)

jev_rule(
    "JEV307", "synonym-cycling", "Cycles synonyms for one referent instead of repeating the word",
    category="Word Choice", source=T, threshold=0.7, default=False,
    explanation="A dashboard becomes an interface, then a portal, then the analytics hub, all for one thing.",
    question={
        "question": "Within this passage, is a single thing referred to by several different synonyms in turn (for "
        "example dashboard, then interface, then portal) instead of repeating one consistent word?",
    },
)

jev_rule(
    "JEV308", "comma-clipped-tail", "A short tail hung off a comma instead of landing the point",
    category="Sentence Structure", source=T, threshold=0.72, default=False,
    explanation="A clipped clause or bare phrase tacked on after a comma to finish sideways.",
    examples=("above the content, and save.", "asked forty times, mentoring."),
    question={
        "question": "Does a sentence here end with a short clause or bare phrase hung off a comma as an afterthought, "
        "instead of landing the point directly?",
    },
)

# Flat certainty (declauding entries 43-47): the register a clean pass lands in once staging is gone, and the
# fastest-growing cluster in the PR-description corpus. These sentences perform having SETTLED a finding --
# adjudicated, verified, exhaustively negated -- the way staging performs having had one. JEV209 (exhaustive
# negation) and CLR013 (the cluster's vocabulary rate) belong to the same family.

jev_rule(
    "JEV309", "certainty-adverb", "A bare adverb asserts the evidence ('plainly', 'provably', 'outright')",
    category="Word Choice", source=f"{D(43)}; {CORPUS}", threshold=0.72, default=False,
    explanation="'plainly', 'quietly', 'outright', 'merely', 'genuinely', 'deliberately', 'provably', "
    "'demonstrably', 'structurally', 'silently'. The adverb asserts the reader's reaction -- that this is obvious, "
    "that the check was real -- where the sentence has not shown it. 'Provably correct' without the proof is "
    "'correct' in a costume. 'plainly' and 'quietly' are the corpus cluster's second and third highest-lift "
    "words. Delete it, or replace it with what makes it true. JEV302 covers adverbs that inflate significance "
    "('fundamentally', 'remarkably'); this one covers adverbs that assert certainty or verification.",
    examples=("The retry is provably safe.", "The flag was quietly dropped in 4.2.", "This is plainly a bug."),
    question={
        "question": "Does this passage use an adverb such as 'plainly', 'provably', 'demonstrably', 'outright', "
        "'merely', 'genuinely', 'deliberately', 'structurally' or 'quietly' to assert that something is obvious, "
        "proven, intended or real, in place of the evidence that would show it?",
        "not_for": "An adverb naming a contrast the reader can check ('silently' against a version that logs, "
        "'identically' against one that differs); an adverb with its evidence beside it; and an adverb that "
        "inflates significance rather than certainty (JEV302).",
    },
)

jev_rule(
    "JEV310", "verification-compound", "A compound claims how it was checked ('byte-identical', 're-derived')",
    category="Word Choice", source=f"{D(45)}; {CORPUS}", threshold=0.7, default=False,
    explanation="'byte-identical', 'bit-for-bit', 'mutation-checked', 'live-verified', 'cross-checked', "
    "'root-caused', 're-derived', 're-verified', 're-measured'. The compound is a claim about method pressed into "
    "an adjective, which puts it past the point where a reader would ask for the method; eleven of the corpus "
    "cluster's top hundred words have this shape, arriving with agents that report on their own work. State "
    "what was run and what came back.",
    examples=("The rewrite is byte-identical and mutation-checked.", "I re-derived the threshold.",
              "Root-caused and live-verified."),
    question={
        "question": "Does this passage use a hyphenated or 're-' compound that asserts how thoroughly something "
        "was checked -- 'byte-identical', 'mutation-checked', 'live-verified', 'cross-checked', 'root-caused', "
        "'re-derived', 're-verified' -- without stating what was run and what result came back?",
        "not_for": "A compound with its evidence beside it (the diff, the command, the counts, the named cause), "
        "and a 're-' verb whose first pass is on the page and whose second pass disagreed with it.",
    },
)

jev_rule(
    "JEV311", "juridical-register", "Code or a process described as a court ('refuses', 'ruling', 'carve-out')",
    category="Word Choice", source=f"{D(44)}; {CORPUS}", threshold=0.72, default=False,
    explanation="'The guard refuses any caller without standing.' 'That is the carve-out the header check "
    "honors.' Legal vocabulary -- refusal, ruling, verdict, precedent, carve-out, standing, remedy, obligation, "
    "honoured -- borrows finality from a domain that has procedures for producing it. A linter does not rule; it "
    "exits non-zero. 'refusal' is the corpus cluster's fourth highest-lift word. Name the mechanism and its exit "
    "condition ('returns 403 when the token has no write scope').",
    examples=("The guard refuses any caller without standing.", "That is the carve-out the header check honors."),
    question={
        "question": "Does this passage describe software, tests or a technical process in legal or courtroom "
        "terms -- refuses, declines, rules, verdict, precedent, carve-out, standing, grounds, remedy, obligation, "
        "honors, ratified -- where naming the actual mechanism and its condition would be clearer?",
        "not_for": "The system's own documented vocabulary (a policy engine whose API says 'deny', an RFC's MUST), "
        "and text that is actually about law, policy or governance.",
    },
)

jev_rule(
    "JEV312", "privative-coinage", "Names a thing by what was not done to it ('ungated', 'unwired', 'vacuous')",
    category="Word Choice", source=f"{D(46)}; {CORPUS}", threshold=0.72, default=False,
    explanation="'Three of the paths are unguarded.' 'The hook is unwired.' 'The assertion is vacuous.' The "
    "coinage sounds like a diagnosis and carries no measurement; several are not words outside this register. "
    "Say what is missing, and where ('three paths have no length check before the index').",
    examples=("Three of the paths are unguarded.", "The hook is unwired.", "The assertion is vacuous."),
    question={
        "question": "Does this passage label something with a coined 'un-' or privative adjective -- ungated, "
        "unguarded, unwired, uncapped, unmeasured, unverifiable, vacuous, inert -- as if it were a diagnosis, "
        "instead of saying what specifically is missing and where?",
        "not_for": "A term of art in the reader's field ('unsatisfiable' in SAT, an 'unbuilt' build target, "
        "'unsigned' integer); and a privative used once to name the finding before the detail that follows it.",
    },
)

# ---------------------------------------------------------------- clarity & grammar, Williams (JEV4xx)

jev_rule(
    "JEV401", "passive-voice", "Passive voice where the actor matters",
    category="Clarity", source=W, threshold=0.7, default=False,
    explanation="Williams, Lesson 3: prefer active voice unless the actor is genuinely unknown or unimportant.",
    examples=("The report was written by the team.",),
    question={
        "question": "Does this passage use passive voice in a way that hides or awkwardly demotes the actor, where "
        "active voice would be clearer?",
        "not_for": "Passive used deliberately because the actor is unknown, obvious, or rightly the focus.",
    },
)

jev_rule(
    "JEV402", "nominalization", "The action is buried in an abstract noun",
    category="Clarity", source=W, threshold=0.7, default=False,
    explanation="Williams, Lesson 2: put actions in verbs. 'make a decision' → 'decide', 'conduct an analysis' → 'analyze'.",
    examples=("We reached a decision.", "The team performed an analysis of the data."),
    question={
        "question": "Does this passage bury its main action in an abstract noun paired with a weak verb ('make a "
        "decision', 'conduct an investigation', 'give consideration to') where a strong verb would be clearer?",
    },
)

jev_rule(
    "JEV403", "wordy-phrase", "A multi-word phrase where one word would do",
    category="Concision", source=W, threshold=0.7,
    explanation="Williams, Lesson 8: 'in order to' → 'to', 'due to the fact that' → 'because', 'at this point in time' → 'now'.",
    examples=("in order to succeed", "due to the fact that costs rose"),
    question={
        "question": "Does this passage use a wordy multi-word phrase that a single word would replace without loss "
        "('in order to', 'due to the fact that', 'at this point in time', 'has the ability to')?",
    },
)

jev_rule(
    "JEV404", "hedging", "Vague hedging that weakens the claim without adding precision",
    category="Clarity", source=W, threshold=0.72, default=False,
    explanation="Piled-up qualifiers ('somewhat', 'arguably', 'in many ways', 'to some extent') that dodge commitment.",
    question={
        "question": "Does this passage hedge a claim with vague qualifiers ('somewhat', 'arguably', 'in many ways', "
        "'to some extent', 'perhaps') in a way that weakens it without adding real precision?",
    },
)

# Compressed syntax (declauding entries 53-56, from Clark, Martin & Mahowald): nothing is staged, but a claim is
# packed into fewer words than a reader can parse. Models overuse these constructions relative to human text in
# the same genre, most in chat and coding-session output. The fix usually makes the sentence LONGER, which is
# why a pass aimed only at brevity produces these shapes instead of removing them.

jev_rule(
    "JEV405", "noun-stack", "Three or more nouns stacked as modifiers ('dry-run write prevention')",
    category="Clarity", source=f"{D(53)}; {COMPRESSION}", threshold=0.72, default=False,
    explanation="'reader-patience budget', 'Policy 1's class-time shutdown requirement', 'dry-run write "
    "prevention'. English never marks how stacked nouns group, so the reader has to work out the bracketing and "
    "supply the relation the writer left out. Unstack into a phrase with prepositions, or a clause that names the "
    "relation ('check that a dry run writes nothing').",
    examples=("New tests for paths with spaces, dry-run write prevention, and idempotent config reinstalls.",
              "Policy 1's class-time shutdown requirement directly addresses this."),
    question={
        "question": "Does this passage stack three or more nouns in a row, each modifying the next (often with a "
        "hyphen fusing two of them), so the reader must work out how they group and what relation links them?",
        "not_for": "An established term in the reader's field ('foreign key constraint', 'money market fund'), a "
        "product or proper name, and a stack the document defines once and then reuses as a name.",
    },
)

jev_rule(
    "JEV406", "verbed-noun", "An ad-hoc noun used as a verb ('footnote it', 'bucket them')",
    category="Clarity", source=f"{D(54)}; {COMPRESSION}", threshold=0.75, default=False,
    explanation="'footnote it', 'calendar it', 'ticket that', 'this papercuts every new user'. Readers parse a "
    "word as the part of speech they expect, so an ad-hoc conversion forces a second look; it saves two words and "
    "spends them back as reanalysis. Use a plain verb with the noun as its object ('move it to a footnote').",
    examples=("Footnote it.", "This papercuts every new user.", "Let's ticket that and bucket the rest."),
    question={
        "question": "Does this passage use a noun as a verb in a way that is not standard ('footnote it', "
        "'calendar it', 'papercuts every user'), forcing the reader to reparse it, where a plain verb with the noun "
        "as its object would read at once?",
        "not_for": "Conversions that are standard in general use or the reader's field ('email', 'bottle', "
        "'scope', 'shard', 'gate a release', 'stage a change'), and quoted speech.",
    },
)

jev_rule(
    "JEV407", "dropped-that", "Optional 'that' left out of a long clause, so the clause boundary is invisible",
    category="Clarity", source=f"{D(55)}; {COMPRESSION}; Levy & Jaeger 2007", threshold=0.75, default=False,
    explanation="'The others check behaviour the old code never reached.' 'We found the cache key omitted the "
    "locale.' People drop 'that' where what follows is predictable and keep it where it is not; without it, two "
    "noun phrases sit side by side and nothing tells the reader a clause has begun. Put 'that' back when the "
    "clause runs past a few words or its subject is a noun phrase the reader has not met.",
    examples=("The others check behaviour the old code never reached.", "We found the cache key omitted the locale."),
    question={
        "question": "Does a sentence here leave out an optional 'that' before a relative or complement clause whose "
        "subject is a new noun phrase or which runs on for several words, so the reader cannot tell where the "
        "clause begins without rereading?",
        "not_for": "A short clause after a common verb where the reader expects it ('the book I read', 'I think "
        "the build is broken').",
    },
)

jev_rule(
    "JEV408", "distant-verb", "Subject held apart from its verb by a list or aside",
    category="Clarity", source=f"{D(56)}; {COMPRESSION}; Gibson 1998", threshold=0.72, default=False,
    explanation="'All five expression shapes -- attribute access, subscript, calls, nested calls, string literals "
    "-- leave current on NAME('b').' The reader holds the subject in memory until the verb arrives, and the cost "
    "grows with the distance. Give the verb early: move the list or aside after the main clause or into its own "
    "sentence.",
    examples=("All five expression shapes -- attribute access, subscript, calls, nested calls, string literals -- "
              "leave current on NAME('b').",),
    question={
        "question": "Does a sentence here hold its subject far apart from its main verb with an inserted list, a "
        "dash-delimited aside or a long appositive, so the reader must carry the subject across it before learning "
        "what it does?",
        "not_for": "A short list of two or three brief items, and a subject that is long because it is a quoted "
        "name or title.",
    },
)

# ---------------------------------------------------------------- Strunk & White, Elements of Style (JEV5xx)
# Composition principles that aren't already covered. Active voice is JEV401, "omit needless words" is
# JEV403 (wordy phrases) plus JEV201 (dilution), and overstatement is JEV101, so those are not repeated.

jev_rule(
    "JEV501", "negative-statement", "Says what something is not, instead of what it is",
    category="Clarity", source=E, threshold=0.7,
    explanation="Elements of Style, rule 15: put statements in positive form. 'not honest' → 'dishonest', "
    "'did not remember' → 'forgot', and avoid the timid 'not un-' construction.",
    examples=("He was not very often on time.", "The plan was not without merit.", "She did not think it was unwise."),
    question={
        "question": "Does this passage make its point by saying what something is NOT, or by negating a negative "
        "('not un-', 'not without'), where a direct positive statement would be crisper?",
        "not_for": "A genuine denial or contrast where the negation carries the real meaning.",
    },
)

jev_rule(
    "JEV502", "vague-abstraction", "Abstract, general language where concrete detail would serve",
    category="Substance", source=E, threshold=0.85,
    skip_for=("notes", "sms", "chat_message", "script"),
    explanation="Elements of Style, rule 16: use definite, specific, concrete language. Prefer the particular fact "
    "to the vague generality; 'a period of unfavorable weather' → 'it rained every day for a week'.",
    examples=("The situation developed in an unsatisfactory manner.",
              "We took steps to address the relevant considerations."),
    question={
        "question": "Is this passage written in vague, abstract, or general terms where concrete, specific, definite "
        "language would carry more meaning?",
        "not_for": "A deliberately terse note, list item, heading, or fragment; a greeting, closing, or short "
        "functional line; a passage that is already specific or a lead-in whose specifics follow immediately.",
    },
)

jev_rule(
    "JEV503", "weak-intensifier", "Leans on 'very', 'rather', 'pretty', 'quite' for emphasis",
    category="Concision", source=E, threshold=0.7,
    explanation="Elements of Style: 'rather, very, little, pretty — these are the leeches that infest the pond of "
    "prose, sucking the blood of words.' The intensifier weakens rather than strengthens.",
    examples=("It was a very interesting and rather unusual result.", "The test was pretty much a success."),
    question={
        "question": "Does this passage lean on a weak degree word — 'very', 'rather', 'pretty', 'quite', 'so', "
        "'little' — to prop up an adjective or adverb, where a stronger single word or none at all would be better?",
        "not_for": "'quite' meaning completely, or a degree word carrying a precise, necessary distinction.",
    },
)

jev_rule(
    "JEV504", "loose-sentence-chain", "Two or more clauses strung together with and / but / so / which",
    category="Sentence Structure", source=E, threshold=0.72, default=False,
    explanation="Elements of Style, rule 20: avoid a succession of loose sentences — clauses tacked on with a "
    "conjunction or a relative 'which', so the sentence rambles instead of being built.",
    examples=("We drove into town and we had lunch and then we looked around, which took a while.",),
    question={
        "question": "Is a sentence here built as a loose string of two or more independent clauses hung together with "
        "'and', 'but', 'so', or a relative 'which', so that it rambles rather than being deliberately constructed?",
    },
)

jev_rule(
    "JEV505", "faulty-parallelism", "Coordinate ideas in a series expressed in mismatched forms",
    category="Sentence Structure", source=E, threshold=0.72, default=False,
    explanation="Elements of Style, rule 19: express coordinate ideas in similar form. Items in a series or a "
    "correlative pair ('both … and', 'not only … but also') should share grammatical structure.",
    examples=("She likes cooking, to jog, and books.", "The plan was both cheap and it worked fast."),
    question={
        "question": "Does this passage list coordinate ideas — in a series, or a 'both/and', 'not only/but also', "
        "'either/or' pair — in mismatched grammatical forms that should be parallel?",
    },
)

# ---------------------------------------------------------------- form-specific rules (JEV6xx)
# Mined from seminal style texts for particular document types; each is gated with applies_to so it
# runs only on the kind of writing it is about. Sources are cited per rule; more than one is fine.

HARGIS = "Hargis et al., Developing Quality Technical Information (IBM)"

jev_rule(
    "JEV601", "not-task-oriented", "Documentation that describes the thing instead of telling the reader how to use it",
    category="Documentation", source=HARGIS, threshold=0.72, default=False, applies_to=("documentation",),
    explanation="Task orientation: docs should help the reader accomplish a task, not just catalog what a "
    "component is. Sources: Hargis et al., Developing Quality Technical Information; Google and Microsoft style guides.",
    examples=("The Config object is a container that holds settings for host, port, and timeout.",),
    question={
        "question": "In a section whose job is to instruct (a how-to, steps, or a task), does this merely describe "
        "what a component is instead of how to accomplish the task with it?",
        "not_for": "An introduction, tagline, overview, conceptual explanation, or a reference/description section "
        "whose purpose is to describe rather than instruct.",
    },
)

jev_rule(
    "JEV602", "undefined-term", "An acronym or specialized term used without being defined on first use",
    category="Documentation", source=f"{HARGIS}; Microsoft Writing Style Guide", threshold=0.8, default=False,
    applies_to=("documentation", "report", "academic_paper"),
    explanation="Clarity/completeness: expand an acronym or define a specialized term the first time it appears. "
    "Sources: Hargis et al., Developing Quality Technical Information; Microsoft Writing Style Guide.",
    examples=("Enable RBAC and apply the CRD before the DaemonSet rolls out.",),
    question={
        "question": "Does this introduce an obscure acronym or specialized term with no expansion or definition, one "
        "that a reader in the intended audience would likely not recognize?",
        "not_for": "Widely-known tech terms and acronyms, product/tool/library names, the document's own defined "
        "terms, or a term the surrounding text defines or links.",
    },
)

jev_rule(
    "JEV603", "diff-anchored-docs", "Documentation that narrates a change instead of describing the current state",
    category="Documentation", source=f"{D(34)}; declauding step 4a (the newcomer read)", threshold=0.72,
    default=False, applies_to=("documentation",),
    explanation="Written from the diff that produced it: 'this function was added to replace', 'we now use', "
    "'the previous approach was', 'pick your options here, upright' (written after the options moved off a "
    "sideways screen). It reads coherently only to someone who saw the last change; six months later nobody did. "
    "Describe how the thing behaves now. The change belongs in the commit message or the changelog. JEV011 "
    "covers notes about edits to the document itself; this covers prose about the thing that leans on its "
    "previous version.",
    examples=("This function was added to replace the previous approach of iterating through all items.",
              "We now store sessions in Redis instead of on disk."),
    question={
        "question": "Does this documentation describe how the thing changed -- what was added, replaced or "
        "updated, what 'now' happens, what the previous approach was -- or lean on an earlier version the reader "
        "never saw, instead of describing how it currently works?",
        "not_for": "Changelogs, release notes, migration and upgrade guides, deprecation notices, and a "
        "'history' or 'background' section whose job is to describe the change.",
    },
)

jev_rule(
    "JEV610", "buried-conclusion", "Makes the reader work through context before stating the conclusion",
    category="Composition", source="Minto, The Pyramid Principle; Garner, HBR Guide to Better Business Writing",
    threshold=0.7, scope="document", applies_to=("report", "memo"),
    explanation="Answer-first / bottom-line-up-front: a report or memo should lead with its recommendation or "
    "conclusion, then support it. Sources: Minto, The Pyramid Principle; Garner, HBR Guide to Better Business Writing.",
    examples=("Weeks of survey, log review, and debate … and only at the end: 'we should adopt structured logging.'",),
    question={
        "question": "Does this piece make the reader work through background, evidence, or process before it states "
        "its main conclusion or recommendation, instead of leading with the answer?",
        "not_for": "A piece whose main point is already stated at or near the start.",
    },
)

jev_rule(
    "JEV620", "editorializing", "Opinion or loaded language inserted into what is presented as reporting",
    category="Substance", source="AP Stylebook; Kovach & Rosenstiel, The Elements of Journalism",
    threshold=0.7, applies_to=("article", "press_release"),
    explanation="News and press writing report; they don't judge. Loaded adjectives and the writer's opinion do not "
    "belong in factual reporting. Sources: AP Stylebook; Kovach & Rosenstiel, The Elements of Journalism.",
    examples=("The company's disastrous and frankly embarrassing rollout proves management still doesn't get it.",),
    question={
        "question": "Does this insert the writer's opinion, or loaded and judgmental adjectives, into what is "
        "presented as factual reporting?",
        "not_for": "A clearly labelled opinion piece, editorial, or a directly attributed quotation.",
    },
)

jev_rule(
    "JEV630", "feature-not-benefit", "Lists features without translating them into a benefit to the reader",
    category="Substance", source="Ogilvy, Ogilvy on Advertising; Bly, The Copywriter's Handbook",
    threshold=0.7, applies_to=("marketing_copy", "product_description"),
    explanation="Sell the benefit, not the spec: copy should say what a feature does for the reader. Sources: "
    "Ogilvy, Ogilvy on Advertising; Bly, The Copywriter's Handbook.",
    examples=("The X200 has a 3nm chip, 16GB RAM, a 6.1-inch OLED panel, and an IP68 rating.",),
    question={
        "question": "Does this list product features or specifications without translating them into a concrete "
        "benefit or outcome for the reader or customer?",
        "not_for": "A spec sheet or table whose explicit purpose is to list specifications.",
    },
)

jev_rule(
    "JEV640", "on-the-nose-dialogue", "Dialogue that states feelings or plot directly instead of implying them",
    category="Substance", source="McKee, Story; Field, Screenplay", threshold=0.72, applies_to=("script",),
    explanation="On-the-nose dialogue says outright what should be implied by subtext or action. Sources: "
    "McKee, Story; Field, Screenplay.",
    examples=("\"I am so angry at you right now because you forgot my birthday,\" she said.",),
    question={
        "question": "Does the dialogue here state characters' feelings, motives, or the plot directly and literally, "
        "where subtext or implication would be stronger?",
    },
)

jev_rule(
    "JEV650", "forced-rhyme", "Rhyme that distorts word choice or syntax to hit the rhyme",
    category="Word Choice", source="Oliver, A Poetry Handbook; Fry, The Ode Less Travelled",
    threshold=0.72, applies_to=("poem",),
    explanation="A rhyme that bends meaning or word order just to land the sound. Sources: Oliver, A Poetry "
    "Handbook; Fry, The Ode Less Travelled.",
    examples=("Inverted syntax or an odd word chosen only because it rhymes with the line before.",),
    question={
        "question": "Does this verse distort its word choice or syntax — an unnatural word or inverted phrasing — "
        "mainly to make a rhyme land?",
    },
)

jev_rule(
    "JEV660", "vague-changelog-entry", "A release note that says nothing specific ('various improvements')",
    category="Substance", source="Keep a Changelog (keepachangelog.com)",
    threshold=0.7, applies_to=("release_notes",),
    explanation="A changelog entry should say what changed. 'Various improvements and bug fixes' tells the reader "
    "nothing. Source: Keep a Changelog (keepachangelog.com).",
    examples=("- Various improvements and bug fixes", "- Minor changes"),
    question={
        "question": "Is this release-note or changelog entry vague ('various improvements', 'bug fixes', 'minor "
        "changes') instead of stating what specifically changed?",
    },
)

jev_rule(
    "JEV670", "weak-resume-bullet", "A resume entry with no strong action verb or concrete result",
    category="Substance", source="Resume conventions (strong action verbs, quantified results)",
    threshold=0.7, applies_to=("resume",),
    explanation="Resume bullets should lead with a strong action verb and state a concrete, ideally quantified "
    "result, not 'Responsible for' or 'Helped with'. Source: widely-held resume conventions.",
    examples=("Responsible for helping with various marketing tasks and assisting the team as needed.",),
    question={
        "question": "Does this resume entry lead with a weak phrase like 'Responsible for' or 'Helped with', or "
        "otherwise lack a strong action verb and a concrete or quantified result?",
    },
)


# ---------------------------------------------------------------- narrative (JEV7xx)
#
# These judge a level above the paragraph: a title, a section with its title and body, or the
# document's outline -- its titles read in order, the way a reader skims a deck or a report's headings
# to follow the argument. See extract.Section and jev.plan_units for what each level is shown.

AE = "Alley, The Craft of Scientific Presentations (assertion-evidence)"
MINTO = "Minto, The Pyramid Principle"

jev_rule(
    "JEV701", "label-title", "A slide title that names a topic instead of stating the slide's point",
    category="Narrative", source=AE, threshold=0.75, scope="title", applies_to=("presentation",),
    explanation="A slide title should be the claim the slide supports ('Efficiency is now the scarce input'), "
    "not a topic label ('Efficiency overview'). A reader who reads only the titles should get the argument. "
    "Cover, agenda, divider and closing titles are exempt. Source: Alley, The Craft of Scientific Presentations.",
    examples=("Market Overview", "Q3 Results", "Our Team"),
    question={
        "question": "Is this slide title a topic label -- it names a subject, like 'Market overview' or 'Q3 "
        "results' -- rather than a claim or finding the slide argues for, which a reader could agree or disagree "
        "with?",
        "not_for": "A title that states a finding, recommendation, or a number with its meaning; and the title "
        "of a cover, agenda, section divider, or closing slide -- the first or last slide, or one with few "
        "words under it that opens a part of the deck -- such as 'What we'll cover', 'The evidence', or "
        "'Thank you'.",
    },
)

jev_rule(
    "JEV702", "title-not-delivered", "A section or slide whose body doesn't support what its title says",
    category="Narrative", source=MINTO, threshold=0.85, scope="section",
    applies_to=("presentation", "report", "memo", "essay", "article", "blog_post"),
    explanation="Each section's body should prove the point its title makes. A body that argues something "
    "else, covers only part of the title, or contradicts it leaves the reader holding a claim nobody "
    "supported. Source: Minto, The Pyramid Principle.",
    examples=("Title 'Churn fell after the pricing change' over a body about hiring.",),
    question={
        "question": "Does the body of this section or slide fail to support or deliver what its title says -- it "
        "argues something else, covers only part of the title's claim, or contradicts it?",
        "not_for": "A body that supports its title, even briefly; a cover, agenda, divider, quote, or closing "
        "slide whose title is not a claim the body argues; and a section with charts_or_images, whose support "
        "is a picture you cannot see -- its caption or source line is not the evidence.",
    },
)

jev_rule(
    "JEV703", "two-points-one-slide", "A slide that makes more than one main point",
    category="Narrative", source=AE, threshold=0.8, scope="section", applies_to=("presentation",), default=False,
    explanation="One slide, one point: a slide that needs two titles to say what it shows is two slides. Off by "
    "default; the call is a judgment. Source: Alley, The Craft of Scientific Presentations.",
    question={
        "question": "Does this slide try to make more than one main point, so that it would need two separate "
        "titles to say what it shows?",
        "not_for": "A slide whose items all support one point, such as several numbers behind one claim.",
    },
)

# Document headings. A deck's titles should be claims (JEV701), and so should a report's or memo's (Minto);
# a doc's or a blog post's headings are navigation, and fail in two opposite directions: a coy or verdict
# heading that performs the finding, and the abstract-noun label written in flight from one.

jev_rule(
    "JEV704", "verdict-heading", "A coy, thesis-shaped or obituary heading where a plain label belongs",
    category="Narrative", source=f"{D(7)}; {D(52)}", threshold=0.75, scope="title", default=False,
    applies_to=("documentation", "blog_post"),
    explanation="Headings in docs and posts are for finding your place. A coy heading ('What actually matters', "
    "'Why this works') could top three different sections; a thesis-shaped one ('The cache was never the "
    "problem') performs the finding before the section shows it; an obituary headline ('Code review is dead', "
    "'Long live X') states a verdict in a form built to overstate, and the body spends its first paragraph "
    "walking it back. Name the content, or name what changed ('Three of four teams dropped second approvals'). "
    "Gated to documentation and blog posts: reports, memos and decks are supposed to state their claims in "
    "their titles.",
    examples=("What actually matters", "The cache was never the problem", "Peer code review is dead"),
    question={
        "question": "Is this heading coy, thesis-shaped or an obituary headline -- a teaser like 'What actually "
        "matters' or 'Why this works' that could head any section, a verdict the section has not yet shown ('The "
        "cache was never the problem'), or an 'X is dead' / 'long live X' / 'the death of X' declaration -- "
        "rather than a plain label for what the section contains?",
        "not_for": "A real question the section answers ('How do I rotate a key?'), a plain descriptive label, a "
        "heading that states a concrete measured fact the section then supports, and a phrase quoted from or "
        "naming something else (a cited post, a product's announced end of life).",
    },
)

jev_rule(
    "JEV705", "abstract-heading", "A heading whose head noun is an abstraction ('Spawn availability')",
    category="Narrative", source=D(41), threshold=0.75, scope="title", default=False, skip_for=("presentation",),
    explanation="'GitHub authorship in a sourced child', 'Spawn availability', 'Detecting a parked child'. A "
    "heading built on an abstract noun (-tion, -ment, -ity, -ship) or a bare gerund names a topic area, so a "
    "reader scanning the outline learns only what they already knew. It is the standard overcorrection from a "
    "verdict heading (JEV704): fleeing a verdict into an abstraction is not a fix. Name the concrete thing, or "
    "ask the reader's question ('Who the delegate posts as', 'When create_session fails').",
    examples=("Spawn availability", "GitHub authorship in a sourced child", "Channels between siblings"),
    question={
        "question": "Is this heading built on an abstract noun or a bare gerund -- like 'Spawn availability', "
        "'Authorship in a sourced child' or 'Detecting a parked child' -- that names a topic area rather than the "
        "concrete thing, behaviour or question the section covers?",
        "not_for": "A single-word heading for a term the document defines ('Calibration', 'Provenance'); "
        "conventional headings such as 'Installation', 'Configuration', 'Usage', 'Introduction' or 'References'; "
        "and the title of a cover, agenda or closing slide.",
    },
)

jev_rule(
    "JEV711", "ghost-deck", "The titles, read in order, don't tell the argument on their own",
    category="Narrative", source=MINTO + "; the consultant's 'ghost deck' test", threshold=0.75,
    scope="document", view="outline", applies_to=("presentation",),
    explanation="Read only the slide titles in order. They should tell the deck's argument: a sequence of "
    "claims that builds to a conclusion. Topic labels, jumps between unrelated points, or no stated "
    "conclusion mean the story lives in the speaker's head, not on the slides. Judged from the outline alone. "
    "Source: Minto, The Pyramid Principle; the 'ghost deck' practice of drafting a deck as its titles first.",
    examples=("Market Context / Portfolio Performance / Portfolio at a Glance / Looking Ahead",),
    question={
        "question": "Read only these titles, in order, as a reader skimming the deck would. Do they fail to tell "
        "the deck's argument on their own -- because most are topic labels, they jump between unrelated points, "
        "or nothing in them states a conclusion or recommendation?",
        "not_for": "An outline whose titles, read alone, state a sequence of claims that build to a conclusion "
        "or an ask. Cover, agenda, divider and closing titles are expected and do not count against it.",
    },
)


# ---------------------------------------------------------------- rules that read fragments
#
# Asked of every block at or above the word floor, including the short labels and bullets that make
# up most of a deck. Each is about word choice or a claim's register, which a fragment shows as well
# as a paragraph does. Every other block rule needs a full paragraph (see jev.DISCOURSE_MIN_WORDS):
# on slide fragments, discourse rules mistake an agenda line for a preamble and a card header for a
# quotable line.

_FRAGMENT_RULES = ("JEV101", "JEV102", "JEV104", "JEV110", "JEV204", "JEV301", "JEV302", "JEV303", "JEV304",
                   "JEV306", "JEV309", "JEV310", "JEV311", "JEV312", "JEV403", "JEV405", "JEV502", "JEV503")
# Not JEV207 (boilerplate): a label is generic by nature -- "Security for machine identity" -- and the
# rule needs a claim to judge.


def _mark_fragment_rules() -> None:
    from dataclasses import replace

    from riff.rules.base import REGISTRY

    for code in _FRAGMENT_RULES:
        REGISTRY[code] = replace(REGISTRY[code], fragments=True)


_mark_fragment_rules()
