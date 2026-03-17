# Leadspicker Skills for Claude Code

A collection of [Claude Code](https://claude.com/claude-code) skills for automating data enrichment, AI-powered classification, personalization, and outreach sequence building in [Leadspicker.com](https://leadspicker.com) projects.

## Skills

### 1. Data Enrichment (`leadspicker-data-enrichment`)

Orchestrates data preparation and enrichment for contacts in Leadspicker projects via REST API. Automatically resolves column dependencies and runs enrichment in the correct order.

**Capabilities:**
- Email finding and validation
- LinkedIn profile enrichment (company description, about me, positions)
- Company website summarization
- Department headcount analysis
- Dependency-aware batch processing

### 2. AI Classifier (`leadspicker-classifier`)

Creates AI-powered classification columns (magic columns) using GPT-4o-Mini. Supports boolean, string, and scored classification modes with smart variable selection.

**Capabilities:**
- Company classification (e.g., "Is this a SaaS company?")
- Person classification (e.g., "Is this person a Sales Manager?")
- Scored classification with confidence (1-10) and reasoning
- Preview-before-launch workflow (test on 5 rows first)
- Batch classification (multiple columns in one session)

### 3. Personalizer (`leadspicker-personalizer`)

Generates short personalization hooks, icebreakers, salutations, and vocatives for cold email campaigns using GPT-4o-Mini. Outputs sentence fragments (≤16 words) to keep AI hallucination under control.

**Capabilities:**
- Company-based hooks (from website summary or LinkedIn description)
- Person-based hooks (from experience, role, or LinkedIn posts)
- LinkedIn posts icebreakers
- Multi-language output (English, Czech, German, Polish, and more)
- Language-specific salutations with proper grammar (e.g., Czech "Dobrý den, pane Nováku")
- Name vocatives for Slavic languages (first name + last name declension)
- Batch personalization pipelines (all hooks + salutations in one go)

### 4. A/B Testing (`leadspicker-ab-testing`)

Splits all contacts from a source Leadspicker project into N equal random batches and distributes them across N target projects for A/B (or A/B/C/…) testing.

**Capabilities:**
- Truly random contact splitting (no fixed seed)
- Auto-create target projects with naming convention `{source_name}_version_a/b/c/…`
- Works with pre-existing target project IDs
- Automatic cleanup: deletes original project (auto-create mode) or removes copied contacts from source (existing projects mode)
- Full verification of contact counts before and after

### 5. Outreach (`leadspicker-outreach`)

Creates outreach sequences (email, LinkedIn, or multi-channel) for Leadspicker projects via the Sequence API. Builds sequences step-by-step with automatic step chaining.

**Capabilities:**
- Email sequences (cold email with follow-ups in the same thread)
- LinkedIn sequences (connection check → DMs or connection request → messages/InMail)
- Multi-channel sequences (email first, then LinkedIn with email fallbacks)
- Conditional branching (already connected vs. not connected, accepted vs. not accepted)
- InMail support (optional, for LinkedIn Premium users only)
- Complete API payload templates for all three sequence types

## How to Use

### Prerequisites

- A [Leadspicker](https://leadspicker.com) account with API access
- Your Leadspicker API key (`x-api-key`)
- A project ID from Leadspicker
- [Claude Code](https://claude.com/claude-code) installed

### Installation

Copy the `SKILL.md` file from the desired skill folder into your Claude Code project directory:

```bash
# For data enrichment
cp leadspicker-data-enrichment/SKILL.md /your-project/SKILL.md

# For AI classification
cp leadspicker-classifier/SKILL.md /your-project/SKILL.md

# For personalization
cp leadspicker-personalizer/SKILL.md /your-project/SKILL.md

# For A/B testing
cp leadspicker-ab-testing/SKILL.md /your-project/SKILL.md

# For outreach sequences
cp leadspicker-outreach/SKILL.md /your-project/SKILL.md
```

Or use multiple skills by placing them in separate subdirectories within your project.

### Usage

Once the skill is loaded in Claude Code, simply describe what you need in natural language:

**Enrichment examples:**
- "Enrich LinkedIn company descriptions for project 12345"
- "Find email addresses and validate them"
- "Get company website summaries and employee counts"

**Classification examples:**
- "Classify if companies are SaaS platforms"
- "Filter only Sales Managers from the contacts"
- "Score how likely each company targets enterprise customers"

**Personalization examples:**
- "Create a website hook for my contacts"
- "Generate Czech salutations with proper vocative"
- "Write icebreakers from LinkedIn posts in German"
- "Full personalization package in Czech"

**A/B testing examples:**
- "Split project 12345 into two equal groups"
- "Create an A/B test with 3 variants for my leads"
- "Divide my contacts across these two projects: 30371, 30400"

**Outreach examples:**
- "Create an email sequence with 3 emails and 3-day delays"
- "Build a LinkedIn outreach sequence with InMail"
- "Create a multi-channel sequence with email and LinkedIn"
- "Delete the current sequence and start over"

The skills will guide you through providing the API key and project ID, then handle the rest automatically.

## License

MIT
