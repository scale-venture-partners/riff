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
choice, JEV4xx clarity & grammar (Williams).
"""

from __future__ import annotations

from riff.rules.base import jev_rule

T = "tropes.fyi"
W = "Williams, Style: Lessons in Clarity and Grace"
E = "Strunk & White, The Elements of Style"

# ---------------------------------------------------------------- structure / composition (JEV0xx)

jev_rule(
    "JEV001", "preamble", "Announces what it is about to say instead of saying it",
    category="Composition", source=T, threshold=0.65, skip_for=("documentation",),
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
    category="Composition", source=T, threshold=0.65, scope="document",
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
    category="Tone", source=T, threshold=0.68,
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
    category="Composition", source=T, threshold=0.7, scope="document", skip_for=("email", "letter"),
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
    category="Substance", source=E, threshold=0.72,
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
