---
paths:
  - "<gitignore-style pattern>"
  - "<gitignore-style pattern>"
description: "<one line: what this rule enforces>"
---

<!-- Authoring template for rule files. Copy, then delete this whole comment block.

     Field values SSOT: .claude/schema/harness.json (rules section). If comments here disagree
     with the schema, THE SCHEMA WINS.

     Judgments this template locks in:
       - paths: notation is block sequence + double quotes, ONE notation only.
         Rejected: inline array paths: [a, b] / comma string paths: "a,b".
         The runtime reads all three; fixing one keeps any checker's parser trivial
         (a validator that read only one of three notations misjudged every rule written
         in the other two)
       - Matching is gitignore syntax (the `ignore` npm package), NOT glob.
         Patterns are relative to the project root; monorepos need the workspace prefix
       - activation_env / activation_values are rejected — runtime never reads them
       - Cursor keys (globs: / alwaysApply:) are forbidden — with no paths:, a file is
         globally injected at session start even if it says alwaysApply: false
       - Global load (no paths:) requires a stated reason in the first paragraph
       - Categories v0: common / workflow / data / model (reserved for a later version: analysis /
         feature / pipeline) — .claude/schema/harness.json rules.categories_v0

     For a global rule: delete the frontmatter paths: block and open the body with
       "This file is globally loaded (no paths:). Reason: <why>."
     Without a reason, adding paths: is the default.

     Registration: add one row to .claude/rules/<category>/INDEX.md.
     Unregistered rules are invisible to the progressive-disclosure path.
-->

# <Rule title>

<One paragraph: what this rule covers. If globally loaded, state the reason here.>

## <Rule heading>

- <rule>. <reason>.
- <rule>. <reason>.

## Anti-patterns

<!-- Device for keeping only checkable rules: a rule that cannot produce an
     Incorrect / Correct pair cannot be checked either, and is a deletion candidate. -->

**Incorrect (<what is wrong>):**

```<language>
<wrong example>
```

**Correct (<what is right>):**

```<language>
<right example>
```

## References

- <path or URL>
